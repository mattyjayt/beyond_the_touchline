"""Server-side replay clock. One session per match, shared by every subscriber
(UI tabs, Claude Code via MCP), so everyone sees the same match second."""

import asyncio
import bisect
import contextlib
from typing import Any

from app.models import Insight, ReplayControl, Snapshot
from app.services.live_state import compute_state
from app.store import Store

TICK_SEC = 0.1
STATE_EVERY_SEC = 30
MATERIAL = {"substitution", "card"}


class ReplaySession:
    def __init__(self, store: Store, match_id: str, speed: float) -> None:
        self.store = store
        self.match = store.matches[match_id]
        self.rosters = store.rosters(match_id)
        self.events = store.events(match_id)
        self._secs = [e.event_sec for e in self.events]
        self.end_sec = self._secs[-1] if self._secs else 0
        self.clock = 0.0
        self.idx = 0  # next event to emit
        self.speed = speed
        self.status: str = "paused"
        self._last_state = 0.0
        self._subs: set[asyncio.Queue] = set()
        self.insights: list[Insight] = store.insights(match_id)

    # ------------------------------------------------------------ messages
    def control_model(self) -> ReplayControl:
        return ReplayControl(status=self.status, speed=self.speed, clock_sec=round(self.clock, 1))

    def state(self, asof: float | None = None):
        return compute_state(
            self.match, self.rosters, self.events, self.clock if asof is None else asof
        )

    def snapshot(self) -> Snapshot:
        return Snapshot(
            control=self.control_model(),
            events=self.events[: self.idx],
            state=self.state(),
            insights=[i for i in self.insights if i.asof_sec <= self.clock],
        )

    def _broadcast(self, type_: str, data: Any) -> None:
        msg = {"type": type_, "data": data}
        for q in list(self._subs):
            with contextlib.suppress(asyncio.QueueFull):
                q.put_nowait(msg)

    def _send_state(self) -> None:
        self._broadcast("state", self.state().model_dump(mode="json"))
        self._last_state = self.clock

    # -------------------------------------------------------- subscribers
    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=10_000)
        q.put_nowait({"type": "snapshot", "data": self.snapshot().model_dump(mode="json")})
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._subs.discard(q)

    # ------------------------------------------------------------- clock
    def advance(self, new_clock: float) -> None:
        new_clock = min(new_clock, self.end_sec)
        # re-surface stored insights the clock passes again (e.g. after a seek back)
        for ins in self.insights:
            if self.clock < ins.asof_sec <= new_clock:
                self._broadcast("insight", ins.model_dump(mode="json"))
        material = False
        while self.idx < len(self.events) and self.events[self.idx].event_sec <= new_clock:
            ev = self.events[self.idx]
            self.clock = ev.event_sec
            self._broadcast("event", ev.model_dump(mode="json"))
            if ev.event_type in MATERIAL or (ev.event_type == "shot" and ev.outcome == "goal"):
                material = True
            self.idx += 1
        self.clock = new_clock
        if material or self.clock - self._last_state >= STATE_EVERY_SEC:
            self._send_state()
        if self.clock >= self.end_sec and self.status != "finished":
            self.status = "finished"
            self._send_state()
            self._broadcast("control", self.control_model().model_dump(mode="json"))

    def control(self, action: str, value: float | None = None) -> ReplayControl:
        if action == "play":
            if self.status == "finished":
                self._seek(0)
            self.status = "playing"
        elif action == "pause":
            self.status = "paused" if self.status != "finished" else "finished"
        elif action == "speed" and value:
            self.speed = max(0.25, min(float(value), 600.0))
        elif action == "seek" and value is not None:
            self._seek(float(value))
        elif action == "restart":
            self._seek(0)
            self.status = "paused"
        else:
            raise ValueError(f"unknown or incomplete control action: {action}")
        self._broadcast("control", self.control_model().model_dump(mode="json"))
        return self.control_model()

    def _seek(self, sec: float) -> None:
        self.clock = max(0.0, min(sec, self.end_sec))
        self.idx = bisect.bisect_right(self._secs, self.clock)
        self._last_state = self.clock
        if self.status == "finished" and self.clock < self.end_sec:
            self.status = "paused"
        self._broadcast("snapshot", self.snapshot().model_dump(mode="json"))

    def publish_insight(self, insight: Insight) -> None:
        self.store.add_insight(insight)
        self.insights.append(insight)
        self._broadcast("insight", insight.model_dump(mode="json"))

    def broadcast_recommendations(self, options: list[dict]) -> None:
        self._broadcast("recommendation", options)

    async def run(self) -> None:
        while True:
            await asyncio.sleep(TICK_SEC)
            if self.status == "playing":
                self.advance(self.clock + self.speed * TICK_SEC)


class ReplayManager:
    def __init__(self, store: Store, speed: float) -> None:
        self.store = store
        self.speed = speed
        self.sessions: dict[str, ReplaySession] = {}
        self._tasks: list[asyncio.Task] = []

    def get(self, match_id: str) -> ReplaySession:
        if match_id not in self.sessions:
            session = ReplaySession(self.store, match_id, self.speed)
            self.sessions[match_id] = session
            self._tasks.append(asyncio.create_task(session.run()))
        return self.sessions[match_id]

    async def close(self) -> None:
        for t in self._tasks:
            t.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)

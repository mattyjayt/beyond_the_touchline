"""REST + SSE routes under /api."""

import asyncio
import json
from typing import Literal

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent import tools
from app.agent.ask import AskRequest, AskResponse, ask
from app.config import get_settings
from app.models import Match, MatchEvent, MatchState, Player, ReplayControl, RosterEntry, Team

router = APIRouter(prefix="/api")


def _store(request: Request):
    return request.app.state.store


def _replays(request: Request):
    return request.app.state.replays


def _match(request: Request, match_id: str) -> Match:
    match = _store(request).matches.get(match_id)
    if match is None:
        raise HTTPException(404, f"match {match_id} not found")
    return match


class MatchDetail(BaseModel):
    match: Match
    home: Team
    away: Team
    roster: list[RosterEntry]
    players: dict[str, Player]
    duration_sec: int


class ControlRequest(BaseModel):
    action: Literal["play", "pause", "speed", "seek", "restart"]
    value: float | None = None


@router.get("/teams")
def teams(request: Request) -> list[Team]:
    return list(_store(request).teams.values())


@router.get("/matches")
def matches(request: Request, kind: Literal["historical", "demo"] | None = None) -> list[Match]:
    return [m for m in _store(request).matches.values() if kind is None or m.kind == kind]


@router.get("/matches/demo")
def demo_match(request: Request) -> MatchDetail:
    return match_detail(request, _store(request).demo_match_id)


@router.get("/matches/{match_id}")
def match_detail(request: Request, match_id: str) -> MatchDetail:
    store = _store(request)
    match = _match(request, match_id)
    roster = store.rosters(match_id)
    return MatchDetail(
        match=match,
        home=store.teams[match.home_team_id],
        away=store.teams[match.away_team_id],
        roster=roster,
        players={r.player_id: store.players[r.player_id] for r in roster},
        duration_sec=store.events(match_id)[-1].event_sec,
    )


@router.get("/matches/{match_id}/events")
def match_events(request: Request, match_id: str, until_sec: int | None = None) -> list[MatchEvent]:
    _match(request, match_id)
    evs = _store(request).events(match_id)
    return evs if until_sec is None else [e for e in evs if e.event_sec <= until_sec]


@router.get("/matches/{match_id}/state")
async def match_state(request: Request, match_id: str, asof_sec: int | None = None) -> MatchState:
    _match(request, match_id)
    return _replays(request).get(match_id).state(asof_sec)


@router.post("/matches/{match_id}/replay")
async def replay_control(request: Request, match_id: str, body: ControlRequest) -> ReplayControl:
    _match(request, match_id)
    try:
        return _replays(request).get(match_id).control(body.action, body.value)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e


@router.get("/matches/{match_id}/stream")
async def match_stream(request: Request, match_id: str) -> StreamingResponse:
    _match(request, match_id)
    session = _replays(request).get(match_id)
    queue = session.subscribe()

    async def gen():
        try:
            while not await request.is_disconnected():
                try:
                    msg = await asyncio.wait_for(queue.get(), timeout=15)
                    yield f"data: {json.dumps(msg)}\n\n"
                except TimeoutError:
                    yield ": keep-alive\n\n"
        finally:
            session.unsubscribe(queue)

    return StreamingResponse(
        gen(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# --------------------------------------------------------------------------- agent


@router.post("/agent/ask")
async def agent_ask(request: Request, body: AskRequest) -> AskResponse:
    _match(request, body.match_id)
    return await ask(body, get_settings().agent_provider)


@router.get("/agent/substitutions")
async def agent_substitutions(request: Request, match_id: str, team_id: str) -> dict:
    _match(request, match_id)
    return await tools.evaluate_substitutions(match_id, team_id)


@router.get("/agent/players/{player_id}")
async def agent_player(request: Request, player_id: str, match_id: str) -> dict:
    _match(request, match_id)
    return await tools.get_player_performance(match_id, player_id)

"""`rules` agent: deterministic triggers -> templated fan/analyst insights.

Always on (spec Phase C: rule-based insight triggers). It needs no model, so the
demo works offline; LLM agents (Claude Code via MCP, the Agent SDK, Foundry
later) add richer narrative on top through the same tools.
"""

import asyncio
import contextlib
import logging

from app.agent import tools
from app.models import Insight, Recommendation
from app.services import advisor
from app.services.matchups import window_label

log = logging.getLogger(__name__)
GENERATOR = "rules-v0"
CHECK_EVERY_SEC = 60  # match seconds between trigger checks


def _lc(text: str) -> str:
    """Lower-case only the first letter (keeps position codes like RW intact)."""
    return text[:1].lower() + text[1:]


def _team_name(team_id: str) -> str:
    return tools.ctx().store.teams[team_id].name


def _insight(match_id: str, cand: dict, audience: str, headline: str, explanation: str,
             uncertainty: str, recommendation_id: str | None = None) -> Insight:  # fmt: skip
    return Insight(
        insight_id=f"INS-{cand['key']}-{audience}",
        kind=cand["kind"],
        match_id=match_id,
        asof_sec=cand["asof_sec"],
        audience=audience,
        headline=headline,
        explanation=explanation,
        evidence_event_ids=cand["evidence_event_ids"],
        recommendation_id=recommendation_id,
        uncertainty=uncertainty,
        generator_version=GENERATOR,
    )


async def render(match_id: str, cand: dict) -> list[Insight]:
    f = cand["facts"]
    kind = cand["kind"]
    if kind == "key_moment":
        state = await tools.get_match_state(match_id, cand["asof_sec"])
        score = f"{state['home']['score']}-{state['away']['score']}"
        team = _team_name(f["team_id"])
        return [
            _insight(match_id, cand, "fan", f"GOAL! {f['scorer']} scores for {team}",
                     f"{f['scorer']} finishes it off. It's {score} in this simulated match.",
                     "Goal is a recorded event; no uncertainty about the fact."),
            _insight(match_id, cand, "analyst", f"Goal · {f['scorer']} ({team}) · xG {f['xg']}",
                     f"Shot quality {f['xg']} xG (illustrative model). Score {score}."
                     + (" Assisted - linked pass in evidence." if len(cand["evidence_event_ids"]) > 1 else ""),
                     "xG is an uncalibrated illustrative model."),
        ]  # fmt: skip
    if kind == "momentum_shift":
        team = _team_name(f["team_id"])
        n = len(cand["evidence_event_ids"])
        return [
            _insight(match_id, cand, "fan", f"{team} are turning the screw",
                     f"{team} have had the better of the last five minutes, with {n} shots or "
                     "successful dribbles.", "Momentum is a short-window heuristic."),
            _insight(match_id, cand, "analyst", f"Momentum swing to {team} (index {f['momentum']:+.0f})",
                     "Rolling 5-min threat index (shots x3 + final-third entries + successful "
                     f"take-ons) favours {team}.", "Heuristic index; small window, high variance."),
        ]  # fmt: skip
    if kind == "tactical_alert":
        pct = "n/a" if f["win_pct_20m"] is None else f"{f['win_pct_20m']:.0%}"
        return [
            _insight(match_id, cand, "fan", f"{f['attacker']} is running riot down the flank",
                     f"{f['attacker']} has beaten {f['defender']} {f['beaten_20m']} times in the "
                     "last 20 minutes of this simulated match.",
                     f"Based on {f['n_20m']} duels; a pattern, not a verdict."),
            _insight(match_id, cand, "analyst",
                     f"Hot duel: {f['attacker']} vs {f['defender_slot']} {f['defender']}",
                     f"Beaten {f['beaten_20m']} in {window_label()} · defender win {pct} (n={f['n_20m']}). "
                     "Duel terms on each event come from the simulator model (uncalibrated).",
                     f"n={f['n_20m']} duels; small samples swing quickly."),
        ]  # fmt: skip
    if kind == "substitution_opportunity":
        team_id = f["team_id"]
        ev = await tools.evaluate_substitutions(match_id, team_id, cand["asof_sec"])
        session = tools.ctx().replays.get(match_id)
        session.broadcast_recommendations(ev["options"])
        changes = [o for o in ev["options"] if o["option_type"] != "keep"]
        keep = next(o for o in ev["options"] if o["option_type"] == "keep")
        if not changes:
            return []
        top = changes[0]
        ranking = "; ".join(f"{o['option_rank']}) {option_label(o)}" for o in ev["options"])
        dims = top["dims"]
        return [
            _insight(match_id, cand, "fan", f"Could a change help {_team_name(team_id)}?",
                     f"{f['attacker']} keeps getting past {f['defender']}. One idea: "
                     f"{_lc(option_label(top))}. Or keep things as they are: {_lc(keep['pros'][0])}.",
                     f"Confidence {top['confidence']}; a scenario, not a prediction.",
                     top["rec_id"]),
            _insight(match_id, cand, "analyst", f"Bench options for {_team_name(team_id)}: {ranking}",
                     f"{ev['diagnosis']}. Top option: {top['pros'][0]}. Dims L {dims['L']:+.2f} "
                     f"F {dims['F']:+.2f} M {dims['M']:+.2f} A {dims['A']:+.2f} G {dims['G']:+.2f} "
                     f"R {dims['R']:+.2f} (policy weights).",
                     f"Confidence {top['confidence']}; policy scores, not causal effects.",
                     top["rec_id"]),
        ]  # fmt: skip
    return []


def option_label(o: dict) -> str:
    """Label for an option dict returned by ``tools.evaluate_substitutions``."""
    names = {pid: p.display_name for pid, p in tools.ctx().store.players.items()}
    return advisor.option_label(Recommendation.model_validate(o), names)


class RulesAgent:
    def __init__(self, match_id: str) -> None:
        self.match_id = match_id
        self.last_check = 0
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task

    async def _loop(self) -> None:
        while True:
            await asyncio.sleep(0.5)
            try:
                await self.check()
            except Exception:  # never let analysis crash the replay
                log.exception("rules agent check failed")

    async def check(self) -> None:
        clock = int(tools.ctx().replays.get(self.match_id).clock)
        self.last_check = min(self.last_check, clock)  # handles seeks backwards
        if clock - self.last_check < CHECK_EVERY_SEC:
            return
        result = await tools.get_insight_candidates(self.match_id, self.last_check, clock)
        self.last_check = clock
        session = tools.ctx().replays.get(self.match_id)
        published = {i.insight_id for i in session.insights}
        for cand in result["candidates"]:
            if f"INS-{cand['key']}-fan" in published:
                continue
            for insight in await render(self.match_id, cand):
                await tools.publish_insight(insight.model_dump())

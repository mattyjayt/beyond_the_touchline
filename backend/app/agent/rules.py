"""`rules` agent: deterministic triggers -> templated fan/analyst insights.

Always on (spec Phase C: rule-based insight triggers). It needs no model, so the
demo works offline; LLM agents (Claude Code via MCP, the Agent SDK, Foundry
later) add richer narrative on top through the same tools.
"""

import asyncio
import contextlib
import logging

from app.agent import tools
from app.models import Insight

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
    if kind == "player_form":
        hist = await tools.get_player_history(f["player_id"])
        base = hist["take_on_success_pct"]
        base_txt = (
            f"{base:.0f}% over his last {hist['sample_size']} matches"
            if base is not None
            else "no reliable baseline"
        )
        pct = 100 * f["won"] / f["attempts"]
        return [
            _insight(match_id, cand, "fan", f"{f['player']} is finding it tough",
                     f"He has won only {f['won']} of {f['attempts']} take-ons in the last 20 "
                     f"minutes, mostly against {f['opponent']}.",
                     f"Based on {f['attempts']} take-ons; simulated match."),
            _insight(match_id, cand, "analyst",
                     f"{f['player']}: take-on success {pct:.0f}% (last 20') vs {base_txt}",
                     f"Primary matchup: {f['opponent']}. Form deviation is negative; investigate "
                     "before acting - low rating is not an automatic substitution.",
                     f"n={f['attempts']} attempts; baseline sample {hist['sample_size']} matches."),
        ]  # fmt: skip
    if kind == "substitution_opportunity":
        team_id = f["team_id"]
        ev = await tools.evaluate_substitutions(match_id, team_id, cand["asof_sec"])
        session = tools.ctx().replays.get(match_id)
        session.broadcast_recommendations(ev["options"])
        subs = [o for o in ev["options"] if o["option_type"] == "substitution"]
        keep = next(o for o in ev["options"] if o["option_type"] == "keep")
        if not subs:
            return []
        top = subs[0]
        ranking = "; ".join(
            f"{o['option_rank']}) " + ("KEEP" if o["option_type"] == "keep"
                                       else f"{o['incoming_name']} for {o['outgoing_name']}")
            for o in ev["options"]
        )  # fmt: skip
        return [
            _insight(match_id, cand, "fan", f"Could a change help {_team_name(team_id)}?",
                     f"{f['player']} has won {f['won']} of {f['attempts']} take-ons. Bringing on "
                     f"{top['incoming_name']} would add a {_lc(top['pros'][0]).removeprefix('fresh ')}. "
                     f"Keeping him {_lc(keep['pros'][0])}.",
                     f"Confidence {top['confidence']}; a scenario, not a prediction.",
                     top["rec_id"]),
            _insight(match_id, cand, "analyst", f"Bench options for {_team_name(team_id)}: {ranking}",
                     f"{ev['diagnosis']}. Goal difference {ev['game_state']['goal_difference']:+d}, "
                     f"{ev['game_state']['subs_remaining']} subs left. Top sub: attack "
                     f"{top['attack_delta_estimate']:+.2f}, control {top['control_delta_estimate']:+.2f}, "
                     f"defensive risk {top['defensive_risk_delta']:+.2f}, fit {top['tactical_fit_score']:.1f}.",
                     f"Heuristic confidence {top['confidence']}; deltas are hypothetical, not causal.",
                     top["rec_id"]),
        ]  # fmt: skip
    return []


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

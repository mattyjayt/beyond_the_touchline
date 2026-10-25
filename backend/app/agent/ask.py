"""Answer a UI question. Provider `claude_code` runs Claude through the Claude
Agent SDK (local Claude Code login / subscription, or ANTHROPIC_API_KEY) with
the shared tools as in-process MCP tools. Falls back to `rules` on any failure.
"""

import json
import logging
import re
from typing import Any

from pydantic import BaseModel

from app.agent import tools

log = logging.getLogger(__name__)
EVIDENCE_RE = re.compile(r"SIM-[A-Z0-9]+-E\d{4}")

SYSTEM_PROMPT = """You are the Match Analyst for "Inside the Game", a SIMULATED football match centre.
Rules (non-negotiable):
- All matches, events, ratings and recommendations are synthetic simulations. Say so when relevant.
- Never compute or invent football facts or numbers. Use ONLY values returned by your tools.
- Cite evidence event IDs exactly as returned (e.g. SIM-001-E0101) in square brackets.
- State uncertainty. A low rating is not an automatic substitution; when discussing changes,
  always mention the KEEP option alongside substitution options.
- You cannot see beyond the current replay clock. Call get_match_state first.
Audience "fan": short, vivid, plain language (<= 90 words).
Audience "analyst": precise, metric-led, include rating/form deviation and option ranking (<= 160 words).
"""


class AskRequest(BaseModel):
    match_id: str
    question: str
    audience: str = "fan"


class AskResponse(BaseModel):
    answer: str
    evidence_event_ids: list[str]
    provider: str
    synthetic: bool = True


def _evidence(match_id: str, text: str) -> list[str]:
    known = {e.event_id for e in tools.ctx().store.events(match_id)}
    seen: list[str] = []
    for m in EVIDENCE_RE.findall(text):
        if m in known and m not in seen:
            seen.append(m)
    return seen


# ------------------------------------------------------------------ claude_code


def _sdk_tools(match_id: str) -> list[Any]:
    from claude_agent_sdk import tool

    def wrap(fn, name: str, description: str, schema: dict):
        @tool(name, description, schema)
        async def _t(args: dict[str, Any]) -> dict[str, Any]:
            try:
                result = await fn(**args)
            except Exception as e:  # noqa: BLE001 - surface tool errors to the model, not as a crash
                return {"content": [{"type": "text", "text": f"error: {e}"}], "is_error": True}
            return {"content": [{"type": "text", "text": json.dumps(result, default=str)}]}

        return _t

    mid = {"match_id": str}
    return [
        wrap(tools.get_match_state, "get_match_state",
             f"Score, formations, on-pitch players with live ratings, bench. match_id is {match_id}.",
             {"match_id": str}),
        wrap(tools.get_player_performance, "get_player_performance",
             "Live metrics + rating with contributing event IDs for one player.",
             {**mid, "player_id": str}),
        wrap(tools.get_player_history, "get_player_history",
             "Baseline from prior simulated matches (sample size included).", {"player_id": str}),
        wrap(tools.get_matchup_analysis, "get_matchup_analysis",
             "Duels between a player and an opponent in this match plus prior meetings.",
             {**mid, "player_id": str, "opponent_id": str}),
        wrap(tools.evaluate_substitutions, "evaluate_substitutions",
             "KEEP + eligible substitution options with scores, pros/cons, evidence.",
             {**mid, "team_id": str}),
        wrap(tools.get_insight_candidates, "get_insight_candidates",
             "Deterministic triggers (goals, momentum, struggling players) since a second.",
             {**mid, "since_sec": int}),
    ]  # fmt: skip


async def ask_claude(req: AskRequest) -> AskResponse:
    from claude_agent_sdk import (
        AssistantMessage,
        ClaudeAgentOptions,
        ResultMessage,
        TextBlock,
        create_sdk_mcp_server,
        query,
    )

    server = create_sdk_mcp_server("itg", tools=_sdk_tools(req.match_id))
    tool_names = [
        f"mcp__itg__{n}"
        for n in (
            "get_match_state", "get_player_performance", "get_player_history",
            "get_matchup_analysis", "evaluate_substitutions", "get_insight_candidates",
        )
    ]  # fmt: skip
    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        mcp_servers={"itg": server},
        tools=[],  # no built-in tools: only the match tools
        allowed_tools=tool_names,
        setting_sources=[],  # isolate from local CLAUDE.md / settings
        max_turns=10,
    )
    prompt = (
        f"match_id={req.match_id}; audience={req.audience}.\n"
        f"Teams: {json.dumps({t: s.name for t, s in tools.ctx().store.teams.items()})}\n"
        f"Question: {req.question}"
    )
    texts: list[str] = []
    final: str | None = None
    async for msg in query(prompt=prompt, options=options):
        if isinstance(msg, AssistantMessage):
            texts.extend(b.text for b in msg.content if isinstance(b, TextBlock))
        elif isinstance(msg, ResultMessage) and getattr(msg, "result", None):
            final = msg.result
    answer = (final or (texts[-1] if texts else "")).strip()
    if not answer:
        raise RuntimeError("empty answer from Claude")
    return AskResponse(
        answer=answer, evidence_event_ids=_evidence(req.match_id, answer), provider="claude_code"
    )


# ------------------------------------------------------------------------ rules


async def ask_rules(req: AskRequest, note: str | None = None) -> AskResponse:
    state = await tools.get_match_state(req.match_id)
    store = tools.ctx().store
    home, away = state["home"], state["away"]
    hn, an = store.teams[home["team_id"]].name, store.teams[away["team_id"]].name
    lines = [
        f"{state['minute']}' — {hn} {home['score']}-{away['score']} {an} (simulated).",
        (
            f"Possession {home['possession_pct']:.0f}%-{away['possession_pct']:.0f}%, "
            f"shots {home['shots']}-{away['shots']}, xG {home['xg']:.2f}-{away['xg']:.2f}."
        ),
    ]
    evidence: list[str] = []
    q = req.question.lower()
    if any(w in q for w in ("sub", "change", "bench", "replace", "wing")):
        team_id = (
            home["team_id"]
            if hn.lower().split()[0] in q or an.lower().split()[0] not in q
            else away["team_id"]
        )
        ev = await tools.evaluate_substitutions(req.match_id, team_id, state["asof_sec"])
        lines.append(f"Diagnosis: {ev['diagnosis']}.")
        for o in ev["options"]:
            label = (
                "KEEP"
                if o["option_type"] == "keep"
                else f"{o['incoming_name']} for {o['outgoing_name']}"
            )
            lines.append(f"{o['option_rank']}) {label} — + {o['pros'][0]}; − {o['cons'][0]}")
        lines.append(ev["caveat"])
        evidence = ev["options"][0]["supporting_event_ids"]
    if note:
        lines.append(f"[{note}]")
    return AskResponse(answer="\n".join(lines), evidence_event_ids=evidence, provider="rules-v0")


async def ask(req: AskRequest, provider: str) -> AskResponse:
    if provider == "claude_code":
        try:
            return await ask_claude(req)
        except Exception as e:  # noqa: BLE001 - any SDK/CLI/auth failure falls back to rules
            log.warning("claude_code provider failed, falling back to rules: %s", e)
            return await ask_rules(
                req, note=f"Claude unavailable ({type(e).__name__}); rules fallback"
            )
    return await ask_rules(req)

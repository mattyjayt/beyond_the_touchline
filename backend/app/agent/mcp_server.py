"""MCP gateway (streamable HTTP, mounted at /mcp). Lets Claude Code - or later
Azure AI Foundry - act as the live analyst using the same tools as the UI."""

from typing import Any

from mcp.server.mcpserver import MCPServer

from app.agent import tools

INSTRUCTIONS = """Beyond the Touchline: SIMULATED football match analysis tools.
Workflow: get_match_state -> get_insight_candidates / get_player_performance /
get_duel_ledger / evaluate_substitutions -> publish_insight (structured, evidence-cited).
Never invent numbers; cite only event IDs returned by tools; include uncertainty; always weigh
a KEEP option against substitutions and position swaps, and never reorder the advisor's
ranking. You cannot see past the replay clock."""

mcp = MCPServer(name="beyond-the-touchline", instructions=INSTRUCTIONS)


@mcp.tool()
async def get_match_state(match_id: str = "SIM-001", asof_sec: int | None = None) -> dict:
    """Score, formations, on-pitch players with live ratings, bench, subs used."""
    return await tools.get_match_state(match_id, asof_sec)


@mcp.tool()
async def get_player_performance(
    player_id: str, match_id: str = "SIM-001", asof_sec: int | None = None
) -> dict:
    """Live metrics and rating (with contributing event IDs) for one player."""
    return await tools.get_player_performance(match_id, player_id, asof_sec)


@mcp.tool()
async def get_player_history(player_id: str, lookback: int = 5) -> dict:
    """Baseline from prior simulated matches only, with sample size."""
    return await tools.get_player_history(player_id, lookback)


@mcp.tool()
async def get_matchup_analysis(
    player_id: str, opponent_id: str, match_id: str = "SIM-001", asof_sec: int | None = None
) -> dict:
    """Duels between two players in the match plus prior meetings."""
    return await tools.get_matchup_analysis(match_id, player_id, opponent_id, asof_sec)


@mcp.tool()
async def evaluate_substitutions(
    team_id: str, match_id: str = "SIM-001", asof_sec: int | None = None
) -> dict:
    """KEEP vs SUB / position SWAP / SUB+SWAP for the team's losing duel: six bounded policy
    dims (L F M A G R), projected vs observed duel win %, pros/cons, evidence, head-to-head."""
    return await tools.evaluate_substitutions(match_id, team_id, asof_sec)


@mcp.tool()
async def get_duel_ledger(
    attacker_id: str,
    slot: str,
    team_id: str,
    match_id: str = "SIM-001",
    asof_sec: int | None = None,
) -> dict:
    """One attacker vs a defending slot (follows whoever holds it, e.g. "RB") or a defender id:
    duels won/lost/recovered/fouls, channel shots and xG, rolling win %, duel points with
    their stored (uncalibrated) model terms, evidence ids."""
    return await tools.get_duel_ledger(match_id, attacker_id, slot, team_id, asof_sec)


@mcp.tool()
async def get_bench_view(
    team_id: str, match_id: str = "SIM-001", asof_sec: int | None = None
) -> dict:
    """The assistant-coach page payload: sticky hot-duel alert, ledger, ranked KEEP/SUB/SWAP
    options, radar cards, sprint race, swap impact once a position change happened."""
    return await tools.get_bench_view(match_id, team_id, asof_sec)


@mcp.tool()
async def get_insight_candidates(
    match_id: str = "SIM-001", since_sec: int = 0, asof_sec: int | None = None
) -> dict:
    """Deterministic triggers since a match second: goals, momentum swings, hot duels."""
    return await tools.get_insight_candidates(match_id, since_sec, asof_sec)


@mcp.tool()
async def publish_insight(
    insight_id: str,
    kind: str,
    audience: str,
    headline: str,
    explanation: str,
    evidence_event_ids: list[str],
    uncertainty: str,
    asof_sec: int,
    match_id: str = "SIM-001",
    recommendation_id: str | None = None,
) -> dict:
    """Publish a grounded insight to the UI agent panel. kind: momentum_shift | player_form |
    tactical_alert | substitution_opportunity | key_moment. audience: fan | analyst.
    Evidence IDs must exist and not be after the replay clock."""
    payload: dict[str, Any] = {
        "insight_id": insight_id, "kind": kind, "match_id": match_id, "asof_sec": asof_sec,
        "audience": audience, "headline": headline, "explanation": explanation,
        "evidence_event_ids": evidence_event_ids, "recommendation_id": recommendation_id,
        "uncertainty": uncertainty, "generator_version": "claude-code-mcp",
    }  # fmt: skip
    return await tools.publish_insight(payload)

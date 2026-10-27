"""Phase B calibration, run in the pre-registered order (docs/schema.md, Phase B items 6-8).

Every step uses historical-squad simulations over SIM_SEED 1-5 (or the demo line-ups simulated
with those seeds for volume), never the chosen demo seed and never post-swap outcomes. Each
step prints what it measured and the value its pre-registered rule selects.

    uv run python -m app.sim.calibrate
"""

import statistics

from app.services import matchups
from app.services.matchups import first_trigger
from app.sim import duel, engine
from app.sim.engine import MatchSim, pick_lineup
from app.sim.generate import (
    DEMO_AWAY,
    DEMO_HOME,
    DEMO_KICKOFF,
    DEMO_MATCH_ID,
    TORMENTOR,
    demo_scenario,
    simulate_history,
)
from app.sim.squads import load_reference

SEEDS = (1, 2, 3, 4, 5)
TAKE_ON_BAND = (0.34, 0.40)  # mean over seeds (real league 36.7%)
TAKE_ON_SEED_BAND = (0.30, 0.44)  # every seed
MAX_DISMISSALS_PER_MATCH = 0.2
SECOND_YELLOW_CANDIDATES = (0.1, 0.05)
MAX_FOCUS_TAKE_ONS_P90 = 18.0
PASS_MULTS = (4.0, 3.0, 2.0, 1.5, 1.0)  # outer
TAKE_ON_MULTS = (2.5, 2.0, 1.5, 1.0)  # inner
Q_CANDIDATES = (0.80, 0.85, 0.90)  # amendment A1
MAX_FIRING = 0.05


def _reference(seed: int):
    teams, players = load_reference(seed)
    squads = {t.team_id: [p for p in players if p.team_id == t.team_id] for t in teams}
    return {t.team_id: t for t in teams}, squads


def league(seed: int) -> dict:
    """Historical take-on success, defender win rate and dismissals for one seed."""
    teams, squads = _reference(seed)
    matches = simulate_history(teams, squads, seed)
    evs = [e for _, _, es in matches for e in es]
    take_ons = [e for e in evs if e.event_type == "take_on"]
    success = sum(e.outcome == "success" for e in take_ons) / len(take_ons)
    dismissals = sum(
        e.event_type == "card" and e.qualifiers.get("card") in ("red", "second_yellow") for e in evs
    )
    return {"take_on_success": success, "dismissals_per_match": dismissals / len(matches),
            "matches": matches}  # fmt: skip


def focus_take_ons_p90(seed: int, pass_mult: float, take_on_mult: float) -> float:
    """Doku's take-on attempts per 90 while the demo scenario is active, demo line-ups."""
    teams, squads = _reference(seed)
    sc = demo_scenario(6.0, take_on_freq_mult=take_on_mult, pass_to_focus_mult=pass_mult)
    sc.forced_swaps = []  # volume only: no swap needed
    home = pick_lineup(teams[DEMO_HOME], squads[DEMO_HOME], _rng(seed), 0.0,
                       sc.forced_lineup[DEMO_HOME])  # fmt: skip
    away = pick_lineup(teams[DEMO_AWAY], squads[DEMO_AWAY], _rng(seed), 0.0,
                       sc.forced_lineup[DEMO_AWAY])  # fmt: skip
    _, _, events = MatchSim(DEMO_MATCH_ID, "demo", home, away, seed, DEMO_KICKOFF, sc).run()
    start, end = sc.window
    end = min(end, events[-1].event_sec)
    n = sum(
        e.event_type == "take_on" and e.player_id == TORMENTOR and start <= e.event_sec <= end
        for e in events
    )
    return n * 90 * 60 / max(1, end - start)


def firing_rate(q: float) -> tuple[int, int]:
    """(matches where the trigger fires at any second for either team, matches) over SEEDS."""
    matchups.HOT_Q = q
    fired = total = 0
    for seed in SEEDS:
        for match, rosters, events in league(seed)["matches"]:
            total += 1
            fired += any(
                first_trigger(events, rosters, team, 5400)[0] is not None
                for team in (match.home_team_id, match.away_team_id)
            )
    return fired, total


def select_q() -> float | None:
    """Amendment A1: first q in Q_CANDIDATES with firing <= MAX_FIRING of historical matches."""
    for q in Q_CANDIDATES:
        fired, total = firing_rate(q)
        ok = fired / total <= MAX_FIRING
        print(f"[10] HOT_Q={q}: fires in {fired}/{total} historical matches"
              f"{'  <- selected' if ok else ''}")  # fmt: skip
        if ok:
            return q
    print("[10] no q keeps firing <= 5%: stop (keep sim-v0.3)")
    return None


A2_GRID = ((1200, 0.90), (1200, 0.95), (1800, 0.90), (1800, 0.95))  # (W seconds, q), in order


def select_a2() -> tuple[int, float, dict] | None:
    """Amendment A2: first (W, q) with historical firing <= 5% for which the demo seed search
    (pre-swap criteria only) finds a seed."""
    from app.config import get_settings
    from app.sim.generate import demo_search

    for window, q in A2_GRID:
        matchups.HOT_WINDOW_SEC = window
        fired, total = firing_rate(q)
        eligible = fired / total <= MAX_FIRING
        print(f"[A2] W={window // 60}' q={q}: fires in {fired}/{total} historical matches"
              f"{'' if eligible else '  (not eligible)'}")  # fmt: skip
        if not eligible:
            continue
        seed = get_settings().sim_seed
        teams, squads = _reference(seed)
        try:
            _, facts = demo_search(teams, squads, seed)
        except RuntimeError as e:
            print(f"[A2] W={window // 60}' q={q}: demo seed search failed ({e})")
            continue
        print(f"[A2] -> W={window // 60}' q={q}: demo found {facts}  <- selected")
        return window, q, facts
    print("[A2] no grid point yields an eligible demo: Phase B stays shelved (sim-v0.3)")
    return None


def _rng(seed: int):
    import random

    return random.Random(f"calibrate-{seed}")


def main() -> None:
    # item 6: dismissals with the current SECOND_YELLOW_FACTOR, fallback list if needed
    for factor in SECOND_YELLOW_CANDIDATES:
        engine.SECOND_YELLOW_FACTOR = factor
        d = statistics.mean(league(s)["dismissals_per_match"] for s in SEEDS)
        print(f"[6] SECOND_YELLOW_FACTOR={factor}: dismissals/match {d:.3f}")
        if d <= MAX_DISMISSALS_PER_MATCH:
            break
    print(f"[6] -> SECOND_YELLOW_FACTOR = {engine.SECOND_YELLOW_FACTOR}")

    # item 7: smallest integer baseline meeting both bands; then m at that baseline
    chosen = None
    for baseline in range(41):
        duel.DUEL_BASELINE = baseline
        rates = [league(s)["take_on_success"] for s in SEEDS]
        mean = statistics.mean(rates)
        ok = TAKE_ON_BAND[0] <= mean <= TAKE_ON_BAND[1] and all(
            TAKE_ON_SEED_BAND[0] <= r <= TAKE_ON_SEED_BAND[1] for r in rates
        )
        print(f"[7] DUEL_BASELINE={baseline}: mean {mean:.3f} per-seed "
              f"{[round(r, 3) for r in rates]}{'  <- selected' if ok else ''}")  # fmt: skip
        if ok:
            chosen = baseline
            m = 1 - mean
            break
    if chosen is None:
        print("[7] no baseline in 0..40 meets the bands: stop (keep sim-v0.3)")
        return
    print(f"[7] -> DUEL_BASELINE = {chosen}; league defender win rate m = {m:.3f}")

    # item 8: volume levers, outer pass multiplier, inner take-on multiplier
    for pm in PASS_MULTS:
        for tm in TAKE_ON_MULTS:
            v = statistics.mean(focus_take_ons_p90(s, pm, tm) for s in SEEDS)
            hit = v <= MAX_FOCUS_TAKE_ONS_P90
            print(f"[8] pass_to_focus_mult={pm} take_on_freq_mult={tm}: "
                  f"{v:.1f} take-ons/90{'  <- selected' if hit else ''}")  # fmt: skip
            if hit:
                print(f"[8] -> DEMO_PASS_MULT = {pm}, DEMO_TAKE_ON_MULT = {tm}")
                return
    print("[8] no lever pair reaches <= 18/90: stop (keep sim-v0.3)")


if __name__ == "__main__":
    import sys

    if sys.argv[1:] == ["q"]:  # step 10 only, with items 6-8 already applied in the code
        select_q()
    elif sys.argv[1:] == ["a2"]:  # amendment A2 grid
        select_a2()
    else:
        main()

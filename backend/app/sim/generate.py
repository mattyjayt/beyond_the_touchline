"""Generate all synthetic data into SQLite.

    uv run python -m app.sim.generate

20 historical fixtures (double round robin of 5 clubs) + the demo match SIM-001
(Liverpool vs Manchester City, simulated) with a scripted storyline: from 50' Jérémy Doku
(MCI, LW) keeps beating Jeremie Frimpong (LIV, RB) in the channel, the generic hot-duel
trigger fires between 55' and 68', and Liverpool swap Szoboszlai (RW) and Frimpong at 70'.
The script only acts while Frimpong holds the RB slot; after the swap every duel is decided
by the unscripted duel model. Deterministic for SIM_SEED; the database is rebuilt from
scratch on every run.
"""

import hashlib
import random
import time
from datetime import UTC, datetime, timedelta

from app import db
from app.config import get_settings
from app.models import MatchEvent, Player, RosterEntry, Team
from app.services.matchups import first_trigger
from app.sim.engine import GENERATOR_VERSION, HALF_SEC, MatchSim, Scenario, pick_lineup
from app.sim.squads import load_reference
from app.sim.validate import validate_match

DEMO_MATCH_ID = "SIM-001"
DEMO_HOME, DEMO_AWAY = "T-LIV", "T-MCI"
DEMO_KICKOFF = datetime(2026, 10, 25, 15, 0, tzinfo=UTC)
SEASON_START = datetime(2026, 8, 15, 15, 0, tzinfo=UTC)

TORMENTOR = "P-MCI-11"  # Jérémy Doku, LW
VICTIM = "P-LIV-30"  # Jeremie Frimpong, RB (the marker in the scripted channel)
SWAP_IN = "P-LIV-08"  # Dominik Szoboszlai, starts at RW; swaps to RB at 70'
BENCH_OPTIONS = ["P-LIV-02", "P-LIV-12"]  # Joe Gomez, Conor Bradley
BOOST_FROM_SEC = 3000  # 50': the scripted duel boost starts
SWAP_SEC = 4200  # 70': forced Szoboszlai <-> Frimpong swap

SCRIPT_BOOSTS = [6.0, 8.0, 10.0, 12.0]  # tried lowest first; the first that passes is kept
SEED_ATTEMPTS = 500
FOLLOWUP_MULT = 2.0  # spec 3.4 follow-up cross/shot boost after a scripted channel win
MIN_BEATS = 6  # Doku beats Frimpong >= 6 times in [BOOST_FROM_SEC, SWAP_SEC)
TRIGGER_FROM, TRIGGER_TO = 3300, 4080  # hot-duel trigger first fires between 55' and 68'
# Swap candidates must match or beat Frimpong on these physical indices (spec 3.4). The
# defensive index is the stance index (side-on defending, sampled from the defending prior).
SWAP_CANDIDATES = [SWAP_IN, BENCH_OPTIONS[0]]  # Szoboszlai, Gomez
PROFILE_INDICES = ("stance_idx", "accel_idx")


def round_robin(team_ids: list[str]) -> list[tuple[str, str]]:
    """Circle method; odd team count gets a bye. Returns both legs."""
    ids = team_ids + (["BYE"] if len(team_ids) % 2 else [])
    n = len(ids)
    first_leg: list[tuple[str, str]] = []
    for rnd in range(n - 1):
        for i in range(n // 2):
            a, b = ids[i], ids[n - 1 - i]
            if "BYE" not in (a, b):
                first_leg.append((a, b) if rnd % 2 == 0 else (b, a))
        ids = [ids[0], ids[-1], *ids[1:-1]]
    return first_leg + [(b, a) for a, b in first_leg]


def demo_scenario(script_boost: float) -> Scenario:
    return Scenario(
        focus_player_id=TORMENTOR,
        marker_id=VICTIM,
        marker_slot="RB",
        # Active from 50' to full time: after the swap Doku still meets the RB slot holder
        # (now Szoboszlai) at the same frequency, but `script` is 0 because Frimpong no longer
        # holds the marked slot, so post-swap outcomes come from the duel model alone.
        window=(BOOST_FROM_SEC, 2 * HALF_SEC + 600),
        script_boost=script_boost,
        followup_mult=FOLLOWUP_MULT,
        forced_lineup={DEMO_HOME: {"RB": VICTIM, "RW": SWAP_IN}, DEMO_AWAY: {"LW": TORMENTOR}},
        bench_must={DEMO_HOME: list(BENCH_OPTIONS)},
        forced_swaps=[(SWAP_SEC, DEMO_HOME, SWAP_IN, VICTIM)],
        no_auto_subs_before={DEMO_HOME: SWAP_SEC + 300},
    )


def score_at(events: list[MatchEvent], team_id: str, sec: int) -> int:
    return sum(
        1
        for e in events
        if e.event_sec <= sec and e.event_type == "shot" and e.outcome == "goal"
        and e.team_id == team_id
    )  # fmt: skip


def storyline(events: list[MatchEvent], rosters: list[RosterEntry]) -> dict | None:
    """Spec 3.4 acceptance on PRE-SWAP events only; None if the seed is rejected."""
    # The seed search NEVER inspects events at or after SWAP_SEC: every criterion is
    # evaluated on this truncated list, so post-swap outcomes cannot influence which seed
    # is chosen (disclosed in docs/schema.md).
    pre = [e for e in events if e.event_sec < SWAP_SEC]
    beats = sum(
        1 for e in pre
        if e.event_type == "take_on" and e.outcome == "success" and e.player_id == TORMENTOR
        and e.opponent_id == VICTIM and e.event_sec >= BOOST_FROM_SEC
    )  # fmt: skip
    if beats < MIN_BEATS:
        return None
    if any(
        e.event_type == "card" and e.qualifiers.get("card") in ("red", "second_yellow") for e in pre
    ):
        return None  # the story needs 11 v 11 at the alert (calibration C6b)
    sec, hot = first_trigger(pre, rosters, DEMO_HOME, TRIGGER_TO)
    if sec is None or sec < TRIGGER_FROM:
        return None
    if not any(h.defender_slot == "RB" and h.attacker_id == TORMENTOR for h in hot):
        return None
    home, away = score_at(pre, DEMO_HOME, sec), score_at(pre, DEMO_AWAY, sec)
    if away - home not in (0, 1):  # level or one behind (calibration C6d)
        return None
    return {"beats": beats, "trigger_sec": sec, "score_at_trigger": f"{home}-{away}"}


def check_swap_candidates(players: dict[str, Player]) -> None:
    """Spec 3.4: Szoboszlai and Gomez match or beat Frimpong on the profile indices.
    Reference data, independent of the match seed, so it is asserted once, not searched."""
    victim = players[VICTIM].physical
    assert victim is not None
    for pid in SWAP_CANDIDATES:
        phys = players[pid].physical
        assert phys is not None
        for idx in PROFILE_INDICES:
            if getattr(phys, idx) < getattr(victim, idx):
                raise RuntimeError(f"{pid} {idx} {getattr(phys, idx)} < Frimpong's")


def demo_search(teams: dict[str, Team], squads: dict[str, list[Player]], seed: int):
    """Search (script_boost outermost, then seeds seed..seed+499) for the first demo that
    satisfies the spec 3.4 storyline, judged on pre-swap events only (see `storyline`)."""
    check_swap_candidates({p.player_id: p for ps in squads.values() for p in ps})
    for boost in SCRIPT_BOOSTS:
        for attempt in range(SEED_ATTEMPTS):
            s = seed + attempt
            sc = demo_scenario(boost)
            rng = random.Random(f"lineup-{DEMO_MATCH_ID}-{s}")
            home = pick_lineup(
                teams[DEMO_HOME], squads[DEMO_HOME], rng, 0.0,
                sc.forced_lineup[DEMO_HOME], sc.bench_must[DEMO_HOME],
            )  # fmt: skip
            away = pick_lineup(
                teams[DEMO_AWAY], squads[DEMO_AWAY], rng, 0.0, sc.forced_lineup[DEMO_AWAY]
            )
            sim = MatchSim(DEMO_MATCH_ID, "demo", home, away, s, DEMO_KICKOFF, sc)
            match, rosters, events = sim.run()
            facts = storyline(events, rosters)
            if facts is None:
                continue
            # Not a selection criterion: a forced swap that silently no-ops is a demo
            # misconfiguration (e.g. a red card before 70'), so fail loudly instead.
            if sim.failed_swaps:
                raise RuntimeError(f"demo seed {s}: forced swap did not happen {sim.failed_swaps}")
            return (match, rosters, events), {"script_boost": boost, **facts}
    raise RuntimeError("no demo seed satisfied the storyline constraints")


def simulate_demo(teams: dict[str, Team], squads: dict[str, list[Player]], seed: int):
    return demo_search(teams, squads, seed)[0]


def simulate_history(teams: dict[str, Team], squads: dict[str, list[Player]], seed: int):
    """The 20 historical fixtures (shared with the hot-duel rarity test)."""
    results = []
    for i, (h, a) in enumerate(round_robin(list(teams))):
        match_id = f"SIM-H{i + 1:02d}"
        kickoff = SEASON_START + timedelta(days=7 * (i // 2), hours=2 * (i % 2))
        rng = random.Random(f"lineup-{match_id}-{seed}")
        home = pick_lineup(teams[h], squads[h], rng, noise=0.25)
        away = pick_lineup(teams[a], squads[a], rng, noise=0.25)
        results.append(MatchSim(match_id, "historical", home, away, seed + i, kickoff).run())
    return results


def event_hash(events: list[MatchEvent]) -> str:
    h = hashlib.sha256()
    for e in events:
        h.update(e.model_dump_json().encode())
    return h.hexdigest()[:16]


def generate(seed: int | None = None) -> dict:
    settings = get_settings()
    seed = settings.sim_seed if seed is None else seed
    teams_list, players = load_reference(seed)
    teams = {t.team_id: t for t in teams_list}
    squads: dict[str, list[Player]] = {t: [] for t in teams}
    for p in players:
        squads[p.team_id].append(p)

    results = simulate_history(teams, squads, seed)
    demo_result, story = demo_search(teams, squads, seed)
    results.append(demo_result)

    for match, rosters, events in results:
        errors = validate_match(match, rosters, events)
        if errors:
            raise ValueError(f"{match.match_id} failed validation:\n  " + "\n  ".join(errors[:20]))

    db_path = settings.database_url.removeprefix("sqlite:///")
    from pathlib import Path

    path = Path(db_path)
    if path.exists():
        path.unlink()
    conn = db.connect(path)
    db.write_reference(conn, teams_list, players)
    for match, rosters, events in results:
        db.write_match(conn, match, rosters, events)
    conn.commit()
    conn.close()

    demo = results[-1][0]
    return {
        "db": str(path),
        "generator_version": GENERATOR_VERSION,
        "matches": len(results),
        "events": sum(len(r[2]) for r in results),
        "demo": f"{demo.match_id} seed={demo.seed} final {demo.home_score}-{demo.away_score}",
        "demo_hash": event_hash(results[-1][2]),
        "demo_story": ", ".join(f"{k}={v}" for k, v in story.items()),
    }


def main() -> None:
    t0 = time.perf_counter()
    summary = generate()
    for k, v in summary.items():
        print(f"  {k:<18} {v}")
    print(f"  {'took':<18} {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()

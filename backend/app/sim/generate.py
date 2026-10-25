"""Generate all synthetic data into SQLite.

    uv run python -m app.sim.generate

20 historical fixtures (double round robin of 5 clubs) + the demo match SIM-001
(Arsenal vs Manchester City) with a scripted storyline: Saka's take-ons dry up
against City's left back from ~48', setting up a substitution question at ~67'.
Deterministic for SIM_SEED; the database is rebuilt from scratch on every run.
"""

import hashlib
import random
import time
from datetime import UTC, datetime, timedelta

from app import db
from app.config import get_settings
from app.models import MatchEvent, Player, Team
from app.sim.engine import GENERATOR_VERSION, MatchSim, Scenario, pick_lineup
from app.sim.squads import load_reference
from app.sim.validate import validate_match

DEMO_MATCH_ID = "SIM-001"
DEMO_HOME, DEMO_AWAY = "T-ARS", "T-MCI"
DEMO_KICKOFF = datetime(2026, 10, 25, 15, 0, tzinfo=UTC)
SEASON_START = datetime(2026, 8, 15, 15, 0, tzinfo=UTC)

FOCUS_PLAYER = "P-ARS-07"  # Bukayo Saka, RW
FOCUS_MARKER = "P-MCI-21"  # Rayan Aït-Nouri, LB
SUB_INCOMING = "P-ARS-56"  # Max Dowman, RW ball carrier
ALT_INCOMING = "P-ARS-20"  # Noni Madueke, RW
ALERT_SEC = 4020  # ~67'
SUB_SEC = 4200  # 70' - the change happens after the alert window


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


def demo_scenario() -> Scenario:
    return Scenario(
        focus_player_id=FOCUS_PLAYER,
        marker_id=FOCUS_MARKER,
        window=(2880, ALERT_SEC + 120),
        forced_lineup={DEMO_HOME: {"RW": FOCUS_PLAYER}, DEMO_AWAY: {"LB": FOCUS_MARKER}},
        bench_must={DEMO_HOME: [SUB_INCOMING, ALT_INCOMING]},
        forced_subs=[(SUB_SEC, DEMO_HOME, FOCUS_PLAYER, SUB_INCOMING)],
        no_auto_subs_before={DEMO_HOME: SUB_SEC + 300},
    )


def score_at(events: list[MatchEvent], team_id: str, sec: int) -> int:
    return sum(
        1
        for e in events
        if e.event_sec <= sec and e.event_type == "shot" and e.outcome == "goal"
        and e.team_id == team_id
    )  # fmt: skip


def simulate_demo(teams: dict[str, Team], squads: dict[str, list[Player]], seed: int):
    """Search seeds deterministically for a demo where the sub question matters:
    Arsenal level or one goal behind at the alert, and at least one goal scored."""
    for attempt in range(500):
        s = seed + attempt
        sc = demo_scenario()
        rng = random.Random(f"lineup-{DEMO_MATCH_ID}-{s}")
        home = pick_lineup(
            teams[DEMO_HOME], squads[DEMO_HOME], rng, 0.0,
            sc.forced_lineup[DEMO_HOME], sc.bench_must[DEMO_HOME],
        )  # fmt: skip
        away = pick_lineup(
            teams[DEMO_AWAY], squads[DEMO_AWAY], rng, 0.0, sc.forced_lineup[DEMO_AWAY]
        )
        result = MatchSim(DEMO_MATCH_ID, "demo", home, away, s, DEMO_KICKOFF, sc).run()
        _, _, events = result
        diff = score_at(events, DEMO_AWAY, ALERT_SEC) - score_at(events, DEMO_HOME, ALERT_SEC)
        goals = score_at(events, DEMO_AWAY, ALERT_SEC) + score_at(events, DEMO_HOME, ALERT_SEC)
        if diff in (0, 1) and goals >= 1:
            return result
    raise RuntimeError("no demo seed satisfied the storyline constraints")


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

    results = []
    for i, (h, a) in enumerate(round_robin(list(teams))):
        match_id = f"SIM-H{i + 1:02d}"
        kickoff = SEASON_START + timedelta(days=7 * (i // 2), hours=2 * (i % 2))
        rng = random.Random(f"lineup-{match_id}-{seed}")
        home = pick_lineup(teams[h], squads[h], rng, noise=0.25)
        away = pick_lineup(teams[a], squads[a], rng, noise=0.25)
        results.append(MatchSim(match_id, "historical", home, away, seed + i, kickoff).run())
    results.append(simulate_demo(teams, squads, seed))

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
    }


def main() -> None:
    t0 = time.perf_counter()
    summary = generate()
    for k, v in summary.items():
        print(f"  {k:<18} {v}")
    print(f"  {'took':<18} {time.perf_counter() - t0:.1f}s")


if __name__ == "__main__":
    main()

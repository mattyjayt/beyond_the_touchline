"""SQLite persistence (local mode). Tables follow docs/schema.md.

Kept to plain SQL with portable types so the same DDL maps onto Azure SQL /
Postgres later; JSON columns are stored as TEXT.
"""

import json
import sqlite3
from pathlib import Path

from app.models import Insight, Match, MatchEvent, Player, RosterEntry, Team

DDL = """
CREATE TABLE IF NOT EXISTS teams (
  team_id TEXT PRIMARY KEY, code TEXT UNIQUE NOT NULL, name TEXT NOT NULL,
  short_name TEXT NOT NULL, home_venue TEXT, primary_color TEXT NOT NULL,
  secondary_color TEXT NOT NULL, manager TEXT, default_formation TEXT NOT NULL,
  strength_index REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS players (
  player_id TEXT PRIMARY KEY, team_id TEXT NOT NULL REFERENCES teams(team_id),
  display_name TEXT NOT NULL, shirt_number INTEGER NOT NULL, primary_position TEXT NOT NULL,
  secondary_positions TEXT NOT NULL, foot TEXT NOT NULL, archetype TEXT NOT NULL,
  priors TEXT,
  physical TEXT
);
CREATE TABLE IF NOT EXISTS matches (
  match_id TEXT PRIMARY KEY, kind TEXT NOT NULL,
  home_team_id TEXT NOT NULL REFERENCES teams(team_id),
  away_team_id TEXT NOT NULL REFERENCES teams(team_id),
  kickoff_at TEXT NOT NULL, status TEXT NOT NULL, home_score INTEGER NOT NULL,
  away_score INTEGER NOT NULL, home_formation TEXT NOT NULL, away_formation TEXT NOT NULL,
  seed INTEGER NOT NULL, generator_version TEXT NOT NULL, synthetic INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS match_rosters (
  match_id TEXT NOT NULL REFERENCES matches(match_id),
  player_id TEXT NOT NULL REFERENCES players(player_id),
  team_id TEXT NOT NULL REFERENCES teams(team_id), roster_status TEXT NOT NULL,
  formation_slot TEXT, shirt_number INTEGER, available INTEGER NOT NULL, reason TEXT,
  PRIMARY KEY (match_id, player_id)
);
CREATE TABLE IF NOT EXISTS events (
  event_id TEXT PRIMARY KEY, match_id TEXT NOT NULL REFERENCES matches(match_id),
  sequence_no INTEGER NOT NULL, period INTEGER NOT NULL, event_sec INTEGER NOT NULL,
  possession_id TEXT, team_id TEXT NOT NULL REFERENCES teams(team_id),
  player_id TEXT REFERENCES players(player_id), event_type TEXT NOT NULL,
  outcome TEXT NOT NULL, start_x REAL, start_y REAL, end_x REAL, end_y REAL,
  recipient_id TEXT REFERENCES players(player_id), opponent_id TEXT REFERENCES players(player_id),
  body_part TEXT, qualifiers TEXT NOT NULL, source_type TEXT NOT NULL,
  UNIQUE (match_id, sequence_no)
);
CREATE INDEX IF NOT EXISTS ix_events_match_sec ON events(match_id, event_sec);
CREATE TABLE IF NOT EXISTS ratings (
  rating_id TEXT PRIMARY KEY, match_id TEXT NOT NULL, player_id TEXT NOT NULL,
  asof_sec INTEGER NOT NULL, live_rating REAL NOT NULL, expected_rating REAL,
  form_delta REAL, role_group TEXT NOT NULL, contributions TEXT NOT NULL,
  low_confidence INTEGER NOT NULL, methodology_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS insights (
  insight_id TEXT PRIMARY KEY, match_id TEXT NOT NULL, asof_sec INTEGER NOT NULL,
  kind TEXT NOT NULL, audience TEXT NOT NULL, headline TEXT NOT NULL, explanation TEXT NOT NULL,
  evidence_event_ids TEXT NOT NULL, recommendation_id TEXT, uncertainty TEXT NOT NULL,
  generator_version TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS recommendations (
  rec_id TEXT PRIMARY KEY, match_id TEXT NOT NULL, team_id TEXT NOT NULL,
  asof_sec INTEGER NOT NULL, payload TEXT NOT NULL, model_version TEXT NOT NULL
);
"""

JSON_COLS = {"secondary_positions", "priors", "physical", "qualifiers", "evidence_event_ids"}


def connect(path: Path) -> sqlite3.Connection:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.executescript(DDL)
    return conn


def _insert(conn: sqlite3.Connection, table: str, rows: list[dict]) -> None:
    if not rows:
        return
    cols = list(rows[0])
    sql = f"INSERT INTO {table} ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})"
    conn.executemany(
        sql, [[json.dumps(r[c]) if c in JSON_COLS else r[c] for c in cols] for r in rows]
    )


def write_reference(conn: sqlite3.Connection, teams: list[Team], players: list[Player]) -> None:
    _insert(conn, "teams", [t.model_dump() for t in teams])
    _insert(conn, "players", [p.model_dump(mode="json") for p in players])


def write_match(
    conn: sqlite3.Connection, match: Match, rosters: list[RosterEntry], events: list[MatchEvent]
) -> None:
    _insert(conn, "matches", [match.model_dump(mode="json")])
    _insert(conn, "match_rosters", [r.model_dump() for r in rosters])
    _insert(conn, "events", [e.model_dump() for e in events])


def write_insight(conn: sqlite3.Connection, insight: Insight) -> None:
    row = insight.model_dump(exclude={"synthetic"})
    _insert(conn, "insights", [row])
    conn.commit()


def _row(r: sqlite3.Row) -> dict:
    # sqlite3.Row iterates values, not keys - .keys() is required here.
    keys = r.keys()
    return {k: json.loads(r[k]) if k in JSON_COLS and r[k] is not None else r[k] for k in keys}


def read_teams(conn: sqlite3.Connection) -> list[Team]:
    return [Team(**_row(r)) for r in conn.execute("SELECT * FROM teams ORDER BY name")]


def read_players(conn: sqlite3.Connection) -> list[Player]:
    rows = conn.execute("SELECT * FROM players ORDER BY team_id, shirt_number")
    return [Player(**_row(r)) for r in rows]


def read_matches(conn: sqlite3.Connection) -> list[Match]:
    rows = conn.execute("SELECT * FROM matches ORDER BY kickoff_at")
    return [Match(**(_row(r) | {"synthetic": True})) for r in rows]


def read_rosters(conn: sqlite3.Connection) -> list[RosterEntry]:
    rows = conn.execute("SELECT * FROM match_rosters")
    return [RosterEntry(**(_row(r) | {"available": bool(r["available"])})) for r in rows]


def read_events(conn: sqlite3.Connection, match_id: str) -> list[MatchEvent]:
    rows = conn.execute("SELECT * FROM events WHERE match_id = ? ORDER BY sequence_no", (match_id,))
    return [MatchEvent(**_row(r)) for r in rows]


def read_insights(conn: sqlite3.Connection, match_id: str) -> list[Insight]:
    rows = conn.execute("SELECT * FROM insights WHERE match_id = ? ORDER BY asof_sec", (match_id,))
    return [Insight(**_row(r)) for r in rows]

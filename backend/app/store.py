"""Read-mostly in-memory view of the SQLite data (small: ~32k events)."""

import sqlite3
from functools import cached_property
from pathlib import Path

from app import db
from app.models import Insight, Match, MatchEvent, Player, RosterEntry, Team


class DataNotGenerated(RuntimeError):
    pass


class Store:
    def __init__(self, path: Path) -> None:
        if not path.exists():
            raise DataNotGenerated(
                f"{path} not found - run scripts/install.sh (or: uv run python -m app.sim.generate)"
            )
        self.conn: sqlite3.Connection = db.connect(path)
        self.teams: dict[str, Team] = {t.team_id: t for t in db.read_teams(self.conn)}
        self.players: dict[str, Player] = {p.player_id: p for p in db.read_players(self.conn)}
        self.matches: dict[str, Match] = {m.match_id: m for m in db.read_matches(self.conn)}
        self._rosters = db.read_rosters(self.conn)
        self._events: dict[str, list[MatchEvent]] = {}

    def rosters(self, match_id: str) -> list[RosterEntry]:
        return [r for r in self._rosters if r.match_id == match_id]

    def events(self, match_id: str) -> list[MatchEvent]:
        if match_id not in self._events:
            self._events[match_id] = db.read_events(self.conn, match_id)
        return self._events[match_id]

    @cached_property
    def demo_match_id(self) -> str:
        return next(m.match_id for m in self.matches.values() if m.kind == "demo")

    def insights(self, match_id: str) -> list[Insight]:
        return db.read_insights(self.conn, match_id)

    def add_insight(self, insight: Insight) -> None:
        db.write_insight(self.conn, insight)

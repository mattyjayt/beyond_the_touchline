"""Load real club/squad reference data and attach synthetic ability priors."""

import json
import random
from pathlib import Path

from app.models import ROLE_GROUP, Player, PlayerPriors, Team

SEED_FILE = Path(__file__).resolve().parents[1] / "seed" / "premier_league_squads.json"

PRIOR_KEYS = ("passing", "dribbling", "finishing", "defending", "physical", "goalkeeping")

ROLE_BASE: dict[str, dict[str, int]] = {
    "GK": {
        "passing": 55,
        "dribbling": 30,
        "finishing": 15,
        "defending": 40,
        "physical": 65,
        "goalkeeping": 80,
    },
    "DEF": {
        "passing": 62,
        "dribbling": 50,
        "finishing": 35,
        "defending": 78,
        "physical": 75,
        "goalkeeping": 10,
    },
    "MID": {
        "passing": 76,
        "dribbling": 68,
        "finishing": 58,
        "defending": 62,
        "physical": 70,
        "goalkeeping": 10,
    },
    "ATT": {
        "passing": 66,
        "dribbling": 78,
        "finishing": 78,
        "defending": 35,
        "physical": 70,
        "goalkeeping": 10,
    },
}

ARCHETYPE_BOOST: dict[str, dict[str, int]] = {
    "shot_stopper": {"goalkeeping": 6},
    "sweeper_keeper": {"passing": 12},
    "ball_playing_cb": {"passing": 8},
    "stopper": {"defending": 6, "physical": 5},
    "attacking_fullback": {"dribbling": 6, "passing": 4, "defending": -4},
    "defensive_fullback": {"defending": 6},
    "inverted_fullback": {"passing": 6},
    "anchor": {"defending": 10},
    "deep_playmaker": {"passing": 10},
    "box_to_box": {"physical": 6, "defending": 4},
    "playmaker": {"passing": 10},
    "advanced_playmaker": {"passing": 9, "dribbling": 3},
    "shadow_striker": {"finishing": 8},
    "direct_winger": {"dribbling": 10, "physical": 3},
    "inside_forward": {"finishing": 6, "dribbling": 5},
    "ball_carrier": {"dribbling": 8, "passing": 2},
    "target_forward": {"physical": 10, "finishing": 4},
    "poacher": {"finishing": 12},
    "complete_forward": {"finishing": 6, "passing": 5},
    "pressing_forward": {"physical": 6, "defending": 6},
}


def load_squads_file(path: Path = SEED_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_reference(seed: int, path: Path = SEED_FILE) -> tuple[list[Team], list[Player]]:
    """Teams and players with synthetic priors. Deterministic for a given seed."""
    data = load_squads_file(path)
    rng = random.Random(f"priors-{seed}")
    teams: list[Team] = []
    players: list[Player] = []
    for t in data["teams"]:
        strength = round(rng.uniform(0.55, 0.85), 3)
        teams.append(
            Team(
                team_id=t["team_id"],
                code=t["code"],
                name=t["name"],
                short_name=t.get("short_name", t["name"]),
                home_venue=t.get("home_venue"),
                primary_color=t["primary_color"],
                secondary_color=t["secondary_color"],
                manager=t.get("manager"),
                default_formation=t.get("default_formation", "4-3-3"),
                strength_index=strength,
            )
        )
        for p in t["players"]:
            group = ROLE_GROUP[p["primary_position"]]
            boost = ARCHETYPE_BOOST.get(p["archetype"], {})
            team_adj = (strength - 0.7) * 20
            priors = {
                k: int(
                    max(
                        20,
                        min(97, ROLE_BASE[group][k] + boost.get(k, 0) + team_adj + rng.gauss(0, 5)),
                    )
                )
                for k in PRIOR_KEYS
            }
            players.append(
                Player(
                    player_id=p["player_id"],
                    team_id=t["team_id"],
                    display_name=p["display_name"],
                    shirt_number=p["shirt_number"],
                    primary_position=p["primary_position"],
                    secondary_positions=p.get("secondary_positions", []),
                    foot=p.get("foot", "right"),
                    archetype=p["archetype"],
                    priors=PlayerPriors(**priors),
                )
            )
    return teams, players

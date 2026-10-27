"""Load real club/squad reference data and attach synthetic ability priors."""

import json
import random
from pathlib import Path

from app.models import ROLE_GROUP, PhysicalProfile, Player, PlayerPriors, Team

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

# Physical sampling. Position buckets: CB, FB (RB/LB/RWB/LWB), CM (CDM/CM/CAM/RM/LM),
# W (RW/LW/RM-wide), ST, GK.
PHYS_BUCKET: dict[str, str] = {
    "GK": "GK",
    "CB": "CB",
    **dict.fromkeys(["RB", "LB", "RWB", "LWB"], "FB"),
    **dict.fromkeys(["CDM", "CM", "CAM", "RM", "LM"], "CM"),
    **dict.fromkeys(["RW", "LW"], "W"),
    "ST": "ST",
}
SPEED_MEAN_KMH = {"CB": 32.5, "FB": 34.0, "CM": 32.5, "W": 34.5, "ST": 33.5, "GK": 29.5}
SPEED_SD_KMH = 1.2
SPEED_RANGE_KMH = (29.0, 37.4)
ACCEL_RANGE = (6.0, 7.9)
# A0 (max starting acceleration) means by bucket, from the research report's LaLiga data
# (CB 6.79, FB 6.70, CM 6.44, W 6.40); ST takes the winger value, GK the floor of the range
A0_MEAN_MS2 = {"CB": 6.79, "FB": 6.70, "CM": 6.44, "W": 6.40, "ST": 6.40, "GK": 6.0}
A0_SD_MS2 = 0.35
A0_RHO = 0.6
STAMINA_MEAN = {"CM": 82, "FB": 80, "W": 74, "CB": 72, "ST": 74, "GK": 60}
HEIGHT_MEAN_CM = {"CB": 188, "FB": 178, "CM": 180, "W": 177, "ST": 184, "GK": 192}

# Fictional prior overrides for the demo story (spec 3.1: Frimpong's defending is "modest").
# Applied after physical sampling, so both random streams stay byte-identical.
PINNED_PRIORS: dict[str, dict[str, int]] = {"P-LIV-30": {"defending": 68}}

# Fictional values for the demo story (docs/superpowers/specs/2026-10-26-subs-advisor-design.md).
# Applied after sampling; keys not listed (e.g. Doku's stance, all heights) stay sampled.
PINNED_PHYSICAL: dict[str, dict] = {
    "P-MCI-11": {"top_speed_kmh": 35.1, "accel_ms2": 7.8, "agility_idx": 95, "stamina_idx": 72},
    "P-LIV-30": {
        "top_speed_kmh": 36.4,
        "accel_ms2": 7.0,
        "agility_idx": 84,
        "stamina_idx": 80,
        "stance_idx": 38,
    },
    "P-LIV-08": {
        "top_speed_kmh": 32.6,
        "accel_ms2": 7.55,
        "agility_idx": 80,
        "stamina_idx": 93,
        "stance_idx": 74,
    },
    "P-LIV-02": {
        "top_speed_kmh": 33.9,
        "accel_ms2": 7.4,
        "agility_idx": 70,
        "stamina_idx": 76,
        "stance_idx": 78,
    },
    "P-LIV-12": {
        "top_speed_kmh": 34.6,
        "accel_ms2": 7.2,
        "agility_idx": 78,
        "stamina_idx": 82,
        "stance_idx": 60,
    },
}


def _clip(value: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, value))


def sample_physical(rng: random.Random, position: str, priors: PlayerPriors) -> PhysicalProfile:
    """Plausible synthetic physical profile; consumes a fixed number of draws per player."""
    bucket = PHYS_BUCKET[position]
    z_speed = rng.gauss(0, 1)
    noise = rng.gauss(0, 1)
    agility_jit = rng.randint(-6, 6)
    stamina_jit = rng.randint(-7, 7)
    stance_jit = rng.randint(-8, 8)
    height_noise = rng.gauss(0, 4)
    speed = _clip(SPEED_MEAN_KMH[bucket] + z_speed * SPEED_SD_KMH, *SPEED_RANGE_KMH)
    # A0 = positional mean + sigma * (rho * z_speed + sqrt(1 - rho^2) * noise): speed and A0
    # correlate at rho (Phase B pre-registration, item 5)
    accel = _clip(
        A0_MEAN_MS2[bucket] + A0_SD_MS2 * (A0_RHO * z_speed + (1 - A0_RHO**2) ** 0.5 * noise),
        *ACCEL_RANGE,
    )
    return PhysicalProfile(
        top_speed_kmh=round(speed, 1),
        accel_ms2=round(accel, 2),
        agility_idx=int(_clip(priors.dribbling + agility_jit, 0, 100)),
        stamina_idx=int(_clip(STAMINA_MEAN[bucket] + stamina_jit, 0, 100)),
        stance_idx=int(_clip(priors.defending + stance_jit, 0, 100)),
        height_cm=round(HEIGHT_MEAN_CM[bucket] + height_noise),
    )


def apply_pin(physical: PhysicalProfile, pin: dict) -> PhysicalProfile:
    """Pinned demo values, validated (model_copy would skip the field bounds)."""
    return PhysicalProfile.model_validate(physical.model_dump() | pin)


def load_squads_file(path: Path = SEED_FILE) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_reference(seed: int, path: Path = SEED_FILE) -> tuple[list[Team], list[Player]]:
    """Teams and players with synthetic priors. Deterministic for a given seed."""
    data = load_squads_file(path)
    rng = random.Random(f"priors-{seed}")
    phys_rng = random.Random(f"physical-{seed}")  # separate stream: priors stay byte-identical
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
            physical = sample_physical(phys_rng, p["primary_position"], PlayerPriors(**priors))
            if p["player_id"] in PINNED_PHYSICAL:
                physical = apply_pin(physical, PINNED_PHYSICAL[p["player_id"]])
            priors.update(PINNED_PRIORS.get(p["player_id"], {}))
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
                    physical=physical,
                )
            )
    return teams, players

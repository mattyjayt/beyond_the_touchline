"""Player metrics, minutes and the illustrative v0 rating (docs/schema.md §7).

Rating v0 is NOT Opta/Sofascore: base 6.0 + bounded, role-weighted event
contributions, clipped to [0, 10]. Every contribution keeps its event_id, so a
rating is fully explainable and reproducible from the event ledger.
"""

from collections import Counter

from app.models import ROLE_GROUP, MatchEvent, Player, RatingContribution, RosterEntry

METHODOLOGY_VERSION = "rating-v0"
BASE_RATING = 6.0
MIN_MINUTES = 15
MIN_ACTIONS = 5

# (event_type, outcome) -> delta for the actor, by role group
WEIGHTS: dict[tuple[str, str], dict[str, float]] = {
    ("pass", "success"): {"GK": 0.01, "DEF": 0.01, "MID": 0.015, "ATT": 0.01},
    ("pass", "fail"): {"GK": -0.04, "DEF": -0.04, "MID": -0.03, "ATT": -0.02},
    ("carry", "fail"): {"GK": -0.1, "DEF": -0.08, "MID": -0.06, "ATT": -0.05},
    ("take_on", "success"): {"GK": 0.1, "DEF": 0.12, "MID": 0.12, "ATT": 0.12},
    ("take_on", "fail"): {"GK": -0.1, "DEF": -0.08, "MID": -0.08, "ATT": -0.08},
    ("shot", "goal"): {"GK": 1.0, "DEF": 1.0, "MID": 1.0, "ATT": 0.9},
    ("shot", "saved"): {"GK": 0.1, "DEF": 0.15, "MID": 0.15, "ATT": 0.12},
    ("shot", "blocked"): {"GK": 0.0, "DEF": 0.02, "MID": 0.02, "ATT": 0.02},
    ("shot", "off_target"): {"GK": -0.05, "DEF": -0.05, "MID": -0.05, "ATT": -0.06},
    ("tackle", "success"): {"GK": 0.15, "DEF": 0.14, "MID": 0.12, "ATT": 0.1},
    ("interception", "success"): {"GK": 0.1, "DEF": 0.12, "MID": 0.1, "ATT": 0.08},
    ("foul", "neutral"): {"GK": -0.1, "DEF": -0.08, "MID": -0.06, "ATT": -0.05},
}
KEY_PASS_BONUS = 0.25
ASSIST_BONUS = 0.6
CARD_DELTA = {"yellow": -0.3, "second_yellow": -1.0, "red": -1.5}
BEATEN_DELTA = -0.06  # defender beaten on a successful take-on


def minutes_played(
    player_id: str, rosters: list[RosterEntry], events: list[MatchEvent], asof: float
) -> float:
    entry = next((r for r in rosters if r.player_id == player_id), None)
    if entry is None:
        return 0.0
    start: float | None = 0.0 if entry.roster_status == "starter" else None
    end = asof
    for e in events:
        if e.event_sec > asof:
            break
        if e.event_type == "substitution":
            if e.recipient_id == player_id:
                start = e.event_sec
            elif e.player_id == player_id:
                end = e.event_sec
        elif (
            e.event_type == "card"
            and e.player_id == player_id
            and e.qualifiers.get("card") in ("red", "second_yellow")
        ):
            end = e.event_sec
    return 0.0 if start is None else max(0.0, (end - start) / 60)


def key_pass_ids(events: list[MatchEvent]) -> tuple[set[str], set[str]]:
    """Derived tags (never separate events): key passes and assists."""
    key, assists = set(), set()
    for e in events:
        if e.event_type == "shot" and (aid := e.qualifiers.get("assist_event_id")):
            key.add(aid)
            if e.outcome == "goal":
                assists.add(aid)
    return key, assists


def player_metrics(player_id: str, events: list[MatchEvent], asof: float) -> dict[str, float]:
    evs = [e for e in events if e.event_sec <= asof]
    mine = [e for e in evs if e.player_id == player_id]
    c = Counter((e.event_type, e.outcome) for e in mine)
    key, assists = key_pass_ids(evs)
    passes = sum(v for (t, _), v in c.items() if t == "pass")
    take_ons = sum(v for (t, _), v in c.items() if t == "take_on")
    shots = [e for e in mine if e.event_type == "shot"]
    return {
        "touches": len([e for e in mine if e.event_type not in ("substitution", "card", "foul")]),
        "passes_attempted": passes,
        "passes_completed": c[("pass", "success")],
        "pass_accuracy": round(100 * c[("pass", "success")] / passes, 1) if passes else 0.0,
        "take_ons_attempted": take_ons,
        "take_ons_won": c[("take_on", "success")],
        "take_on_success_pct": round(100 * c[("take_on", "success")] / take_ons, 1)
        if take_ons
        else 0.0,
        "shots": len(shots),
        "shots_on_target": sum(1 for e in shots if e.outcome in ("goal", "saved")),
        "goals": c[("shot", "goal")],
        "xg": round(sum(float(e.qualifiers.get("xg", 0)) for e in shots), 2),
        "key_passes": sum(1 for e in mine if e.event_id in key),
        "assists": sum(1 for e in mine if e.event_id in assists),
        "tackles_won": c[("tackle", "success")],
        "interceptions": c[("interception", "success")],
        "fouls": c[("foul", "neutral")],
        "cards": c[("card", "neutral")],
    }


def live_rating(
    player: Player, events: list[MatchEvent], asof: float, minutes: float
) -> tuple[float, list[RatingContribution], bool]:
    group = ROLE_GROUP[player.primary_position]
    evs = [e for e in events if e.event_sec <= asof]
    key, assists = key_pass_ids(evs)
    contribs: list[RatingContribution] = []
    actions = 0
    for e in evs:
        if e.player_id == player.player_id:
            w = WEIGHTS.get((e.event_type, e.outcome))
            if w:
                actions += 1
                contribs.append(
                    RatingContribution(
                        event_id=e.event_id, delta=w[group], reason=f"{e.event_type}:{e.outcome}"
                    )
                )
            if e.event_id in assists:
                contribs.append(
                    RatingContribution(event_id=e.event_id, delta=ASSIST_BONUS, reason="assist")
                )
            elif e.event_id in key:
                contribs.append(
                    RatingContribution(event_id=e.event_id, delta=KEY_PASS_BONUS, reason="key_pass")
                )
            if e.event_type == "card":
                card = str(e.qualifiers.get("card"))
                contribs.append(
                    RatingContribution(
                        event_id=e.event_id, delta=CARD_DELTA.get(card, 0), reason=f"card:{card}"
                    )
                )
        elif (
            e.opponent_id == player.player_id
            and e.event_type == "take_on"
            and e.outcome == "success"
        ):
            contribs.append(
                RatingContribution(event_id=e.event_id, delta=BEATEN_DELTA, reason="beaten")
            )
    rating = max(0.0, min(10.0, BASE_RATING + sum(c.delta for c in contribs)))
    low_conf = minutes < MIN_MINUTES or actions < MIN_ACTIONS
    return round(rating, 2), contribs, low_conf

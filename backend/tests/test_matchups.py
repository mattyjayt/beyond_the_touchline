"""Matchup services (spec §4): pure functions over plain event/roster lists."""

import random
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.config import get_settings
from app.models import MatchEvent, RosterEntry
from app.services.matchups import (
    current_slots,
    duel_ledger,
    first_trigger,
    hot_duels,
    hot_pair,
    matchup_map,
    swap_impact,
)
from app.sim.engine import MatchSim, Scenario, Side, mirror, pick_lineup
from app.sim.formations import formation_slots
from app.sim.squads import load_reference

DOKU, FRIMPONG, SZOBOSZLAI, GOMEZ = "P-MCI-11", "P-LIV-30", "P-LIV-08", "P-LIV-02"
MID = "SIM-T06"
TERMS = {"tech": 1.0, "burst": 2.0, "agil": 0.5, "stance": 0.4, "touch": 10.0, "ctx": 1.0,
         "script": 0.0, "z": 0.3, "p_beat": 0.5, "p_recover": 0.1}  # fmt: skip


# ----------------------------------------------------------------- builders
def roster(pid: str, team: str, status: str = "starter", slot: str | None = None) -> RosterEntry:
    return RosterEntry(match_id=MID, player_id=pid, team_id=team, roster_status=status,
                       formation_slot=slot)  # fmt: skip


ROSTERS = [
    roster("P-LIV-01", "T-LIV", slot="GK"),
    roster(FRIMPONG, "T-LIV", slot="RB"),
    roster(SZOBOSZLAI, "T-LIV", slot="RW"),
    roster("P-LIV-04", "T-LIV", slot="RCB"),
    roster("P-LIV-05", "T-LIV", slot="LCB"),
    roster(GOMEZ, "T-LIV", status="bench"),
    roster("P-MCI-31", "T-MCI", slot="GK"),
    roster(DOKU, "T-MCI", slot="LW"),
    roster("P-MCI-09", "T-MCI", slot="ST"),
]


class Events:
    """Hand-built event list with engine-like adjacency (take-on -> tackle/foul)."""

    def __init__(self) -> None:
        self.items: list[MatchEvent] = []
        self.poss = 0

    def add(self, sec: int, etype: str, outcome: str, team: str, player: str | None, **kw):
        n = len(self.items) + 1
        ev = MatchEvent(event_id=f"{MID}-E{n:04d}", match_id=MID, sequence_no=n,
                        period=1 if sec < 2700 else 2, event_sec=sec, team_id=team,
                        player_id=player, event_type=etype, outcome=outcome, **kw)  # fmt: skip
        self.items.append(ev)
        return ev

    def new_poss(self) -> str:
        self.poss += 1
        return f"{MID}-P{self.poss:04d}"

    def take_on(self, sec: int, ok: bool, *, att=DOKU, dfn=FRIMPONG, y=80.0, then=None):
        """`then`: None, "recovery" or "foul" (only after a success)."""
        p = self.new_poss()
        ev = self.add(sec, "take_on", "success" if ok else "fail", "T-MCI", att,
                      possession_id=p, start_x=70.0, start_y=y, opponent_id=dfn,
                      qualifiers={"duel": TERMS})  # fmt: skip
        if not ok:
            self.add(sec, "tackle", "success", "T-LIV", dfn, possession_id=self.new_poss(),
                     start_x=30.0, start_y=100 - y, opponent_id=att)  # fmt: skip
        elif then == "recovery":
            self.add(sec, "tackle", "success", "T-LIV", dfn, possession_id=self.new_poss(),
                     start_x=24.0, start_y=100 - y, opponent_id=att,
                     qualifiers={"recovery": True})  # fmt: skip
        elif then == "foul":
            self.add(sec, "foul", "neutral", "T-LIV", dfn, start_x=24.0, start_y=100 - y,
                     opponent_id=att)  # fmt: skip
        return ev

    def foul(self, sec: int, *, dfn=FRIMPONG, att=DOKU):
        return self.add(sec, "foul", "neutral", "T-LIV", dfn, start_x=25.0, start_y=15.0,
                        opponent_id=att)  # fmt: skip


def ledger_events() -> list[MatchEvent]:
    """3 take-on successes (1 recovered), 2 fails, 1 standalone foul."""
    ev = Events()
    ev.take_on(100, True)
    ev.take_on(200, True, then="recovery")
    ev.take_on(300, True)
    ev.take_on(400, False)
    ev.take_on(500, False)
    ev.foul(600)
    return ev.items


# ---------------------------------------------------------------- geometry
def test_matchup_map_lw_faces_rb():
    m = matchup_map("4-2-3-1", "4-2-3-1")
    assert m["RB"] == "LW"
    assert m["LB"] == "RW"


def _engine_defender_of(our: str, their: str) -> dict[str, str]:
    """Their slot -> our slot the ENGINE picks as defender (engine nearest(), mirrored point)."""
    _, ours = formation_slots(our)
    _, theirs = formation_slots(their)
    side = Side(team=None, formation=our, slots=ours, bench=[],
                on_pitch={s.slot: SimpleNamespace(player_id=s.slot) for s in ours})  # fmt: skip
    return {
        t.slot: MatchSim.nearest(None, side, mirror(t.x, t.y)).player_id  # type: ignore[arg-type]
        for t in theirs
        if t.slot != "GK"
    }


@pytest.mark.parametrize(("our", "their"), [("4-2-3-1", "4-2-3-1"), ("4-3-3", "4-2-3-1"),
                                            ("4-2-3-1", "4-3-3"), ("4-3-3", "4-3-3")])  # fmt: skip
def test_matchup_map_agrees_with_engine_nearest(our, their):
    m = matchup_map(our, their)
    assert "GK" not in m and "GK" not in m.values()
    engine = _engine_defender_of(our, their)
    for s, t in m.items():
        assigned = {att for att, dfn in engine.items() if dfn == s}
        if assigned:  # whenever the engine sends attackers at our slot, ours is one of them
            assert t in assigned, (s, t, assigned)


def test_matchup_map_central_pairing():
    m = matchup_map("4-2-3-1", "4-2-3-1")
    engine = _engine_defender_of("4-2-3-1", "4-2-3-1")
    # engine nearest(): their RCB and LCB in possession are met by our ST (tie -> RCB first),
    # their RDM / LDM by our CAM. Expected values come from the engine, not by hand.
    assert engine["RCB"] == "ST" and engine["LCB"] == "ST"
    assert engine["RDM"] == "CAM" and engine["LDM"] == "CAM"
    assert m["ST"] == "RCB"
    assert m["CAM"] == "RDM"
    # our LCB is never picked by the engine (RCB wins the tie): falls back to the attacker
    # nearest under the same defender-scaled metric
    assert "LCB" not in engine.values() and m["LCB"] == "ST"


# ------------------------------------------------------------------ slots
def test_current_slots_applies_subs_swaps_and_red_cards():
    ev = Events()
    ev.add(100, "position_change", "neutral", "T-LIV", SZOBOSZLAI, recipient_id=FRIMPONG,
           qualifiers={"from_slot": "RW", "to_slot": "RB"})  # fmt: skip
    ev.add(100, "position_change", "neutral", "T-LIV", FRIMPONG, recipient_id=SZOBOSZLAI,
           qualifiers={"from_slot": "RB", "to_slot": "RW"})  # fmt: skip
    ev.add(200, "substitution", "neutral", "T-LIV", FRIMPONG, recipient_id=GOMEZ)
    ev.add(300, "card", "neutral", "T-LIV", "P-LIV-04", qualifiers={"card": "red"})

    before = current_slots(ROSTERS, ev.items, 99)
    assert before[FRIMPONG] == "RB" and before[SZOBOSZLAI] == "RW"
    swapped = current_slots(ROSTERS, ev.items, 100)
    assert swapped[FRIMPONG] == "RW" and swapped[SZOBOSZLAI] == "RB"
    subbed = current_slots(ROSTERS, ev.items, 250)
    assert FRIMPONG not in subbed and subbed[GOMEZ] == "RW"
    final = current_slots(ROSTERS, ev.items, 400)
    assert "P-LIV-04" not in final
    assert final[DOKU] == "LW"  # both teams are included


# ----------------------------------------------------------------- ledger
def test_ledger_counts_won_lost_recovered():
    led = duel_ledger(ledger_events(), DOKU, FRIMPONG, "T-LIV", ROSTERS, asof=900)
    assert led.duels == 6
    assert led.won == 3  # 2 fails + 1 recovery
    assert led.lost == 2  # beaten without recovery
    assert led.recoveries == 1
    assert led.fouls == 1
    assert led.win_pct == pytest.approx(0.5)
    assert led.defender_ids == [FRIMPONG]
    assert led.confidence == "low"  # 3 of 6: the 95% interval is +/- 0.31
    assert [p.outcome for p in led.points] == ["lost", "recovered", "lost", "won", "won", "foul"]
    assert led.points[0].terms == TERMS and led.points[-1].terms == {}
    # every point and its linked tackle/foul is cited
    ids = {e.event_id for e in ledger_events()}
    assert set(led.evidence_event_ids) <= ids
    assert {p.event_id for p in led.points} <= set(led.evidence_event_ids)


def test_ledger_respects_asof_and_since():
    evs = ledger_events()
    assert duel_ledger(evs, DOKU, FRIMPONG, "T-LIV", ROSTERS, asof=250).duels == 2
    assert duel_ledger(evs, DOKU, FRIMPONG, "T-LIV", ROSTERS, asof=900, since=300).duels == 4
    empty = duel_ledger(evs, DOKU, FRIMPONG, "T-LIV", ROSTERS, asof=50)
    assert empty.duels == 0 and empty.win_pct is None and empty.confidence == "low"
    assert empty.defender_rating_swing is None


def test_ledger_rating_swing_uses_rating_weights():
    led = duel_ledger(ledger_events(), DOKU, FRIMPONG, "T-LIV", ROSTERS, asof=900)
    # 3 beaten (-0.06 each), 3 tackles won as DEF (+0.14 each), 1 foul as DEF (-0.08)
    assert led.defender_rating_swing == pytest.approx(3 * -0.06 + 3 * 0.14 - 0.08)


def test_confidence_bands():
    def n_duels(n: int) -> str:
        ev = Events()
        for i in range(n):
            ev.take_on(100 + 10 * i, False)
        return duel_ledger(ev.items, DOKU, FRIMPONG, "T-LIV", ROSTERS, asof=5000).confidence

    # bands follow the 95% Wilson half-width (C4): high needs a tight interval, not just n
    assert [n_duels(n) for n in (3, 4, 9, 10)] == ["low", "low", "medium", "medium"]
    assert n_duels(40) == "high"


def test_rolling_window_600s():
    led = duel_ledger(ledger_events(), DOKU, FRIMPONG, "T-LIV", ROSTERS, asof=900)
    secs = [r.sec for r in led.rolling]
    assert secs == list(range(0, 901, 60))
    by_sec = {r.sec: r for r in led.rolling}
    assert by_sec[60].n == 0 and by_sec[60].win_pct is None
    assert by_sec[600].n == 6 and by_sec[600].win_pct == pytest.approx(0.5)
    assert by_sec[720].n == 5  # sec 100 left the (120, 720] window
    assert by_sec[900].n == 3  # (300, 900]: two fails + the foul
    assert by_sec[900].win_pct == pytest.approx(2 / 3, abs=1e-3)


def test_channel_threat_counts_shots_in_channel_possessions():
    ev = Events()
    t = ev.take_on(100, True, y=80.0)  # in the channel (y > 67 vs a right-sided defender)
    ev.add(105, "shot", "saved", "T-MCI", DOKU, possession_id=t.possession_id, start_x=88.0,
           start_y=60.0, body_part="left_foot", qualifiers={"xg": 0.12})  # fmt: skip
    t2 = ev.take_on(200, True, y=50.0)  # central: not the channel
    ev.add(205, "shot", "off_target", "T-MCI", "P-MCI-09", possession_id=t2.possession_id,
           start_x=85.0, start_y=50.0, body_part="right_foot", qualifiers={"xg": 0.3})  # fmt: skip
    p3 = ev.new_poss()
    ev.add(300, "carry", "success", "T-MCI", DOKU, possession_id=p3, start_x=60.0, start_y=75.0,
           end_x=70.0, end_y=78.0)  # fmt: skip
    ev.add(304, "shot", "goal", "T-MCI", "P-MCI-09", possession_id=p3, start_x=90.0,
           start_y=50.0, body_part="head", qualifiers={"xg": 0.25})  # fmt: skip
    led = duel_ledger(ev.items, DOKU, "RB", "T-LIV", ROSTERS, asof=1000)
    assert led.channel_shots == 2
    assert led.channel_xg == pytest.approx(0.37)
    assert led.duels == 2


def test_ledger_by_slot_follows_occupant():
    ev = Events()
    ev.take_on(100, True, dfn=FRIMPONG)
    ev.add(200, "position_change", "neutral", "T-LIV", SZOBOSZLAI, recipient_id=FRIMPONG,
           qualifiers={"from_slot": "RW", "to_slot": "RB"})  # fmt: skip
    ev.add(200, "position_change", "neutral", "T-LIV", FRIMPONG, recipient_id=SZOBOSZLAI,
           qualifiers={"from_slot": "RB", "to_slot": "RW"})  # fmt: skip
    ev.take_on(300, False, dfn=SZOBOSZLAI)
    ev.take_on(400, True, dfn=FRIMPONG, y=20.0)  # Frimpong now at RW: not the RB duel
    led = duel_ledger(ev.items, DOKU, "RB", "T-LIV", ROSTERS, asof=1000)
    assert led.defender_ids == [FRIMPONG, SZOBOSZLAI]
    assert [(p.defender_id, p.outcome) for p in led.points] == [
        (FRIMPONG, "lost"),
        (SZOBOSZLAI, "won"),
    ]
    by_player = duel_ledger(ev.items, DOKU, FRIMPONG, "T-LIV", ROSTERS, asof=1000)
    assert by_player.duels == 2 and by_player.defender_ids == [FRIMPONG]


# -------------------------------------------------------------- hot duels
# Amended trigger (Phase B A1): >= 3 beaten possessions, P(win rate < league) >= HOT_Q,
# and channel threat (>= 1 shot or >= 2 crosses/box entries) in the last 20 minutes.
def _shot(ev: "Events", poss: str, sec: int) -> None:
    ev.add(sec, "shot", "saved", "T-MCI", DOKU, possession_id=poss, start_x=88.0, start_y=60.0,
           body_part="left_foot", qualifiers={"xg": 0.1})  # fmt: skip


def _beaten_with_threat(secs=(1000, 1100, 1200, 1300, 1400)) -> "Events":
    ev = Events()
    for i, sec in enumerate(secs):
        t = ev.take_on(sec, True)  # each beat in its own possession, in the RB channel
        if i == 0:
            _shot(ev, t.possession_id, sec + 3)
    return ev


def test_trigger_fires_with_beaten_possessions_posterior_and_threat():
    from app.services.matchups import HOT_Q, p_below_league

    ev = _beaten_with_threat()
    hot = hot_duels(ev.items, ROSTERS, "T-LIV", 1450)
    assert p_below_league(0, 5) >= HOT_Q  # 5 straight losses clear q = 0.95
    assert len(hot) == 1
    h = hot[0]
    assert (h.defender_id, h.defender_slot, h.attacker_id) == (FRIMPONG, "RB", DOKU)
    assert (h.beaten_20m, h.n_20m, h.threat_shots_20m) == (5, 5, 1)
    assert h.p_below_league == pytest.approx(p_below_league(0, 5), abs=1e-3)


def test_trigger_needs_threat_from_the_flank():
    ev = Events()
    for sec in (1000, 1100, 1200, 1300):
        ev.take_on(sec, True)
    assert hot_duels(ev.items, ROSTERS, "T-LIV", 1350) == []  # beaten, but no threat


def test_trigger_needs_three_distinct_possessions():
    ev = Events()
    for poss_start in (1000, 1200):  # two runs of three beats each
        p = ev.new_poss()
        for k in range(3):
            ev.add(poss_start + 3 * k, "take_on", "success", "T-MCI", DOKU, possession_id=p,
                   start_x=70.0, start_y=80.0, opponent_id=FRIMPONG,
                   qualifiers={"duel": TERMS})  # fmt: skip
        _shot(ev, p, poss_start + 10)
    assert hot_duels(ev.items, ROSTERS, "T-LIV", 1300) == []  # 6 losses, 2 possessions


def test_trigger_respects_the_posterior():
    from app.services.matchups import HOT_Q, p_below_league

    ev = _beaten_with_threat((1000, 1100, 1200))
    for sec in (1250, 1260, 1270, 1280):
        ev.take_on(sec, False)  # four wins: 3 of 7 lost
    fires = p_below_league(4, 7) >= HOT_Q
    assert bool(hot_duels(ev.items, ROSTERS, "T-LIV", 1300)) is fires
    assert not fires  # winning 4 of 7 is not worse than a league-average defender


def test_first_fired_is_when_the_threat_arrives():
    ev = Events()
    ts = [ev.take_on(sec, True) for sec in (1000, 1050, 1100, 1150, 1200)]
    assert hot_duels(ev.items, ROSTERS, "T-LIV", 1250) == []
    _shot(ev, ts[1].possession_id, 1260)
    h = hot_duels(ev.items, ROSTERS, "T-LIV", 1300)[0]
    assert h.first_fired_sec == 1260
    assert first_trigger(ev.items, ROSTERS, "T-LIV", 1300)[0] == 1260


def test_trigger_switches_off_when_beats_leave_the_window():
    ev = _beaten_with_threat()
    assert hot_duels(ev.items, ROSTERS, "T-LIV", 2150)  # all inside (950, 2150]
    assert hot_duels(ev.items, ROSTERS, "T-LIV", 2250) == []  # beats have left the window


# ------------------------------------------------- in-memory demo-like match
@pytest.fixture(scope="module")
def reference():
    teams, players = load_reference(get_settings().sim_seed)
    squads = {t.team_id: [p for p in players if p.team_id == t.team_id] for t in teams}
    return {t.team_id: t for t in teams}, squads


SWAP_SEC = 4200


@pytest.fixture(scope="module")
def swap_match(reference):
    """LIV vs MCI with Frimpong at RB and a forced Szoboszlai <-> Frimpong swap at 70'."""
    teams, squads = reference
    sc = Scenario(
        focus_player_id=DOKU, window=(3000, SWAP_SEC), marker_id=FRIMPONG, marker_slot="RB",
        forced_lineup={"T-LIV": {"RB": FRIMPONG, "RW": SZOBOSZLAI}, "T-MCI": {"LW": DOKU}},
        forced_swaps=[(SWAP_SEC, "T-LIV", SZOBOSZLAI, FRIMPONG)],
        no_auto_subs_before={"T-LIV": 5280},
    )  # fmt: skip
    rng = random.Random("matchups-test")
    home = pick_lineup(teams["T-LIV"], squads["T-LIV"], rng, 0.0, sc.forced_lineup["T-LIV"])
    away = pick_lineup(teams["T-MCI"], squads["T-MCI"], rng, 0.0, sc.forced_lineup["T-MCI"])
    kickoff = datetime(2026, 9, 1, tzinfo=UTC)
    _, rosters, events = MatchSim(MID, "demo", home, away, 7, kickoff, sc).run()
    return rosters, events


def test_ledger_follows_slot_after_swap_in_memory(swap_match):
    rosters, events = swap_match
    led = duel_ledger(events, DOKU, "RB", "T-LIV", rosters, asof=5000)
    assert led.defender_ids == [FRIMPONG, SZOBOSZLAI]
    assert {p.defender_id for p in led.points if p.sec >= SWAP_SEC} <= {SZOBOSZLAI}
    assert current_slots(rosters, events, 5000)[SZOBOSZLAI] == "RB"
    assert all(e.event_sec <= 5000 for e in events if e.event_id in led.evidence_event_ids)


def test_swap_impact_in_memory(swap_match):
    rosters, events = swap_match
    assert swap_impact(events, rosters, "T-LIV", DOKU, "RB", asof=4000) is None
    imp = swap_impact(events, rosters, "T-LIV", DOKU, "RB", asof=5200)
    assert imp is not None
    assert imp.swap_sec >= SWAP_SEC
    assert imp.before.defender_ids == [FRIMPONG]
    assert imp.after.defender_ids == [SZOBOSZLAI]
    # before = the 20 minutes ahead of the swap (the trigger's window), so per-10 rates compare
    # like with like rather than a 70-minute span against a short post-swap one
    assert all(imp.swap_sec - 1200 <= p.sec < imp.swap_sec for p in imp.before.points)
    assert all(imp.swap_sec <= p.sec <= 5200 for p in imp.after.points)
    b, a = imp.before, imp.after
    assert b.window_sec == 1200  # [swap_sec - 1200, swap_sec - 1]
    assert a.window_sec == 5200 - imp.swap_sec + 1
    poss = {e.event_id: e.possession_id for e in events}
    for led in (b, a):
        beaten_poss = {
            poss[p.event_id] for p in led.points
            if p.outcome == "lost" or (p.outcome == "foul" and p.terms != {})
        }  # fmt: skip
        assert led.beaten == len(beaten_poss)  # one beaten per possession (Phase B item 9)
        assert led.beaten_per_10 == round(led.beaten * 600 / led.window_sec, 2)
    empty = duel_ledger(events, DOKU, "RB", "T-LIV", rosters, asof=100, since=200)
    assert empty.window_sec <= 0 and empty.beaten_per_10 is None


# ------------------------------------------------ demo data (regenerated SIM-001)
@pytest.fixture(scope="module")
def demo():
    from app.store import Store

    store = Store(Path(get_settings().database_url.removeprefix("sqlite:///")))
    return store.rosters("SIM-001"), store.events("SIM-001")


def test_ledger_follows_slot_after_swap(demo):
    rosters, events = demo
    led = duel_ledger(events, DOKU, "RB", "T-LIV", rosters, asof=5000)
    assert led.defender_ids == [FRIMPONG, SZOBOSZLAI]


def test_swap_impact_none_before_swap(demo):
    rosters, events = demo
    assert swap_impact(events, rosters, "T-LIV", DOKU, "RB", asof=4000) is None


def test_swap_impact_after_swap(demo):
    rosters, events = demo
    imp = swap_impact(events, rosters, "T-LIV", DOKU, "RB", asof=5400)
    assert imp is not None
    assert imp.before.defender_ids == [FRIMPONG]
    assert imp.after.defender_ids == [SZOBOSZLAI]


# ------------------------------------------- C1: stats belong to the current holder
def _swapped_after_six_beats() -> list[MatchEvent]:
    ev = _beaten_with_threat((1000, 1100, 1200, 1300, 1400, 1500))  # Frimpong beaten 6 times
    ev.add(1600, "position_change", "neutral", "T-LIV", SZOBOSZLAI, recipient_id=FRIMPONG,
           qualifiers={"from_slot": "RW", "to_slot": "RB"})  # fmt: skip
    ev.add(1600, "position_change", "neutral", "T-LIV", FRIMPONG, recipient_id=SZOBOSZLAI,
           qualifiers={"from_slot": "RB", "to_slot": "RW"})  # fmt: skip
    return ev.items


def test_hot_duels_never_label_a_new_holder_with_old_stats():
    evs = _swapped_after_six_beats()
    assert hot_duels(evs, ROSTERS, "T-LIV", 1550)[0].defender_id == FRIMPONG
    assert hot_duels(evs, ROSTERS, "T-LIV", 1700) == []  # Szoboszlai has no duels yet


def test_hot_pair_reports_holder_and_slot_history_separately():
    evs = _swapped_after_six_beats()
    h = hot_pair(evs, ROSTERS, "T-LIV", "RB", DOKU, 1700, 1500)
    assert h.defender_id == SZOBOSZLAI
    assert (h.n_20m, h.beaten_20m, h.win_pct_20m) == (0, 0, None)
    assert (h.slot_n_20m, h.slot_beaten_20m) == (6, 6)
    assert h.slot_win_pct_20m == 0.0


# ------------------------------------------------------- C4: honest uncertainty
def test_win_interval_is_wilson_and_needs_five_duels():
    ev = Events()
    for i, ok in enumerate([False] * 3 + [True] * 11):  # defender wins 3 of 14
        ev.take_on(100 + 10 * i, ok)
    led = duel_ledger(ev.items, DOKU, FRIMPONG, "T-LIV", ROSTERS, asof=1000)
    lo, hi = led.win_ci
    assert lo == pytest.approx(0.076, abs=0.002) and hi == pytest.approx(0.476, abs=0.002)
    few = duel_ledger(ev.items, DOKU, FRIMPONG, "T-LIV", ROSTERS, asof=130)
    assert few.duels == 4 and few.win_ci is None


def test_rates_hidden_for_windows_under_five_minutes():
    evs = ledger_events()
    short = duel_ledger(evs, DOKU, FRIMPONG, "T-LIV", ROSTERS, asof=450, since=200)
    assert short.window_sec == 251 and short.beaten_per_10 is None
    full = duel_ledger(evs, DOKU, FRIMPONG, "T-LIV", ROSTERS, asof=900, since=200)
    assert full.beaten_per_10 is not None


def test_swap_impact_is_honest_about_overlap_and_shows_a_trajectory(swap_match):
    rosters, events = swap_match
    imp = swap_impact(events, rosters, "T-LIV", DOKU, "RB", asof=5400)
    b, a = imp.before.win_ci, imp.after.win_ci
    separated = b is not None and a is not None and (b[1] < a[0] or a[1] < b[0])
    assert imp.win_separated is separated
    assert [t.minutes for t in imp.trajectory] == [
        m for m in (5, 10, 20) if imp.swap_sec + m * 60 - 1 <= 5400
    ]
    assert imp.trajectory and imp.trajectory[0].minutes == 5
    for t in imp.trajectory:
        led = duel_ledger(events, DOKU, "RB", "T-LIV", rosters,
                          asof=imp.swap_sec + t.minutes * 60 - 1, since=imp.swap_sec)  # fmt: skip
        assert (t.n, t.win_pct) == (led.duels, led.win_pct)
    early = swap_impact(events, rosters, "T-LIV", DOKU, "RB", asof=imp.swap_sec + 100)
    assert early.after.beaten_per_10 is None and early.trajectory == []


# ------------------------------------------------------ C9: threat from the channel
def test_channel_shots_respect_since():
    ev = Events()
    p = ev.new_poss()
    ev.add(
        298,
        "shot",
        "blocked",
        "T-MCI",
        "P-MCI-09",
        possession_id=p,
        start_x=86.0,
        start_y=60.0,
        body_part="right_foot",
        qualifiers={"xg": 0.2},
    )  # before `since`
    ev.add(305, "take_on", "success", "T-MCI", DOKU, possession_id=p, start_x=70.0,
           start_y=80.0, opponent_id=FRIMPONG, qualifiers={"duel": TERMS})  # fmt: skip
    led = duel_ledger(ev.items, DOKU, "RB", "T-LIV", ROSTERS, asof=900, since=300)
    assert led.channel_shots == 0 and led.channel_xg == 0


def test_channel_entries_count_crosses_and_box_entries():
    ev = Events()
    t = ev.take_on(100, True, y=80.0)
    ev.add(
        104,
        "pass",
        "success",
        "T-MCI",
        DOKU,
        possession_id=t.possession_id,
        start_x=80.0,
        start_y=85.0,
        end_x=94.0,
        end_y=50.0,
        recipient_id="P-MCI-09",
        qualifiers={"cross": True},
    )  # completed cross
    t2 = ev.take_on(200, True, y=80.0)
    ev.add(
        203,
        "carry",
        "success",
        "T-MCI",
        DOKU,
        possession_id=t2.possession_id,
        start_x=75.0,
        start_y=78.0,
        end_x=86.0,
        end_y=70.0,
    )  # carried into the box
    t3 = ev.take_on(300, True, y=80.0)
    ev.add(
        303,
        "pass",
        "fail",
        "T-MCI",
        DOKU,
        possession_id=t3.possession_id,
        start_x=80.0,
        start_y=85.0,
        end_x=94.0,
        end_y=50.0,
        qualifiers={"cross": True},
    )  # cut out: no
    led = duel_ledger(ev.items, DOKU, "RB", "T-LIV", ROSTERS, asof=1000)
    assert led.channel_entries == 2 and led.channel_shots == 0


def test_records_vs_matches_per_defender_ledgers(swap_match):
    from app.services.matchups import records_vs

    rosters, events = swap_match
    rec = records_vs(events, rosters, "T-LIV", DOKU, 5000)
    for pid in (FRIMPONG, SZOBOSZLAI, GOMEZ):
        led = duel_ledger(events, DOKU, pid, "T-LIV", rosters, 5000)
        assert rec.get(pid, (0, 0)) == (led.won, led.duels)


# ------------------------------------------------------------- C12: edge cases
def test_no_hot_duel_once_the_tormentor_has_left():
    ev = _beaten_with_threat((1000, 1100, 1200, 1300, 1400, 1500))
    assert hot_duels(ev.items, ROSTERS, "T-LIV", 1550)
    ev.add(1600, "substitution", "neutral", "T-MCI", DOKU, recipient_id="P-MCI-47")
    assert hot_duels(ev.items, ROSTERS, "T-LIV", 1650) == []


# ------------------------------------------- Phase B item 9: one beaten per possession
def test_beaten_counts_once_per_possession():
    ev = Events()
    p = ev.new_poss()
    for sec in (100, 103, 106):  # three beats in one 6-second run
        ev.add(sec, "take_on", "success", "T-MCI", DOKU, possession_id=p, start_x=70.0,
               start_y=80.0, opponent_id=FRIMPONG, qualifiers={"duel": TERMS})  # fmt: skip
    ev.take_on(300, True)  # a separate possession
    led = duel_ledger(ev.items, DOKU, FRIMPONG, "T-LIV", ROSTERS, asof=900)
    assert led.duels == 4 and led.lost == 4
    assert led.beaten == 2  # distinct possessions in which he was beaten


def test_sticky_alert_keeps_the_pair_after_it_goes_quiet():
    from app.services.matchups import sticky_alert

    ev = _beaten_with_threat((1000, 1100, 1200, 1300, 1400))
    fired, hot, active = sticky_alert(ev.items, ROSTERS, "T-LIV", 1450)
    assert fired is not None and active and hot.defender_id == FRIMPONG
    later = sticky_alert(ev.items, ROSTERS, "T-LIV", 2900)  # beats have left the window
    assert later[0] == fired and later[1].defender_slot == "RB" and later[2] is False
    assert sticky_alert(ev.items, ROSTERS, "T-LIV", 900) == (None, None, False)

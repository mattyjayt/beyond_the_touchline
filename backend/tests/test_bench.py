"""GET /api/matches/{id}/bench (Task 9): one payload for the assistant-coach page."""

import pytest

MATCH, TEAM = "SIM-001", "T-LIV"
ALERT_SEC = 3333  # first hot-duel trigger in the sim-v0.4 demo (docs/schema.md §11)
SWAP_SEC = 4223  # the scripted 70' swap lands at the next stoppage


@pytest.fixture
def seek(app_client):
    def _seek(sec: int) -> None:
        r = app_client.post(f"/api/matches/{MATCH}/replay", json={"action": "seek", "value": sec})
        assert r.status_code == 200

    yield _seek
    _seek(4020)  # leave the shared session where test_agent expects it


def bench(client, asof: int | None = None) -> dict:
    params = {"team_id": TEAM} | ({"asof_sec": asof} if asof is not None else {})
    r = client.get(f"/api/matches/{MATCH}/bench", params=params)
    assert r.status_code == 200, r.text
    return r.json()


def test_bench_before_alert(app_client, seek):
    seek(5400)
    v = bench(app_client, 1200)
    assert v["asof_sec"] == 1200 and v["synthetic"] is True
    assert v["alert"] is None and v["impact"] is None and v["ledger"] is None
    assert [o["option_type"] for o in v["options"]] in ([], ["keep"])


def test_bench_one_second_before_alert(app_client, seek):
    seek(5400)
    v = bench(app_client, ALERT_SEC - 1)
    assert v["alert"] is None and v["impact"] is None


def test_bench_clamped_to_clock(app_client, seek):
    seek(4000)
    v = bench(app_client, 9999)
    assert v["asof_sec"] == 4000
    assert v["ledger"]["points"]
    assert all(p["sec"] <= 4000 for p in v["ledger"]["points"])
    assert all(r["sec"] <= 4000 for r in v["ledger"]["rolling"])
    assert v["impact"] is None  # the 70' swap is in the future


def test_bench_at_alert_has_everything(app_client, seek):
    seek(5400)
    v = bench(app_client, ALERT_SEC)
    assert v["alert"]["first_fired_sec"] == ALERT_SEC and v["alert_active"] is True
    assert v["alert"]["defender_slot"] == "RB" and v["alert"]["attacker_id"] == "P-MCI-11"
    assert v["ledger"]["points"]
    assert len(v["race"]["curves"]) >= 3
    assert v["race"]["curves"][0]["player_id"] == "P-MCI-11"
    assert len(v["options"]) >= 3
    assert sum(o["option_type"] == "keep" for o in v["options"]) == 1
    assert v["tormentor"]["player_id"] == "P-MCI-11"
    assert v["defender"]["player_id"] == "P-LIV-30" and v["defender"]["slot"] == "RB"
    # every player an option moves has a radar card with all 7 axes on 0-100
    for o in v["options"]:
        for m in o["moves"]:
            card = v["cards"][m["player_id"]]
            assert set(card["profile"]) == {
                "pace", "acceleration", "agility", "stamina", "defending", "stance", "duel_win"
            }  # fmt: skip
            assert all(0 <= x <= 100 for x in card["profile"].values())
    assert v["briefing_seed"] and "KEEP" in v["briefing_seed"]
    assert v["synthetic"] is True


def test_bench_after_swap_has_impact(app_client, seek):
    seek(5400)
    v = bench(app_client)
    assert v["asof_sec"] == 5400
    imp = v["impact"]
    assert imp is not None and imp["swap_sec"] >= 4200
    assert imp["before"]["defender_ids"] == ["P-LIV-30"]
    assert imp["after"]["defender_ids"] == ["P-LIV-08"]
    # the alert stays (sticky) and now follows the new RB holder
    assert v["alert"]["first_fired_sec"] == ALERT_SEC
    assert v["defender"]["player_id"] == "P-LIV-08"
    # honest comparison with the advisor's ranking at the alert (spec 7.8)
    # ranked among every option scored at the alert (sim-v0.4 demo: 9th of 17, below KEEP)
    assert v["executed_option_rank_at_alert"] == 9 and v["alert_option_count"] == 17
    assert v["executed_below_keep"] is True
    assert v["ledger"]["defender_ids"] == ["P-LIV-30", "P-LIV-08"]
    # C1: the alert's numbers are Szoboszlai's own, the slot history is separate
    assert v["alert"]["defender_id"] == "P-LIV-08"
    assert v["alert"]["slot_n_20m"] >= v["alert"]["n_20m"]


@pytest.mark.parametrize("asof", [SWAP_SEC, SWAP_SEC + 100])
def test_bench_new_holder_is_monitored_not_blamed(app_client, seek, asof):
    seek(5400)
    v = bench(app_client, asof)
    a = v["alert"]
    assert a["defender_id"] == "P-LIV-08"
    own = [
        p
        for p in v["ledger"]["points"]
        if p["defender_id"] == "P-LIV-08" and p["sec"] > asof - 1200
    ]
    assert a["n_20m"] == len(own) < 4
    assert v["alert_state"] == "monitoring"
    assert [o["option_type"] for o in v["options"]] == ["keep"]
    # no text pins Frimpong's 20' record (beaten 8, n=14) on Szoboszlai
    texts = [v["briefing_seed"]] + [c for o in v["options"] for c in o["pros"] + o["cons"]]
    for sentence in (s for t in texts for s in t.split(". ")):
        if "Szoboszlai" in sentence:
            assert "n=14" not in sentence and "beaten 8" not in sentence, sentence


def test_bench_unknown_match_404(app_client):
    assert app_client.get("/api/matches/SIM-999/bench", params={"team_id": TEAM}).status_code == 404


def test_bench_carries_slots_and_importance_note(app_client, seek):
    seek(5400)
    at_alert = bench(app_client, ALERT_SEC)
    assert at_alert["slots"]["P-LIV-30"] == "RB" and at_alert["slots"]["P-LIV-08"] == "RW"
    assert all(pid.startswith("P-LIV") for pid in at_alert["slots"])
    after = bench(app_client, 5000)
    assert after["slots"]["P-LIV-08"] == "RB"
    if after["importance"]:
        assert "methodology demo" in after["importance_note"]


def test_briefing_names_the_model_drivers(app_client, seek):
    seek(5400)
    v = bench(app_client, ALERT_SEC)
    assert "stance" in v["briefing_seed"] and "transition" in v["briefing_seed"]


def test_bench_shows_flank_threat_honestly(app_client, seek):
    seek(5400)
    v = bench(app_client, ALERT_SEC)
    t = v["threat"]
    assert set(t) >= {"shots", "xg", "entries", "threatening"}
    assert t["threatening"] == (t["shots"] >= 1 or t["entries"] >= 2)
    if t["shots"] == 0:
        assert "no shots conceded from this flank yet" in v["briefing_seed"]


# --------------------------------------------------------------- C10: speed
def test_bench_view_is_fast_when_warm(app_client, seek):
    import time

    from app.services.bench import build_bench_view

    seek(5400)
    st, rp = app_client.app.state.store, app_client.app.state.replays
    build_bench_view(st, rp, MATCH, TEAM, 4800)  # warm the static caches
    t = time.perf_counter()
    build_bench_view(st, rp, MATCH, TEAM, 4800)
    assert (time.perf_counter() - t) * 1000 < 60


async def test_bench_tool_does_not_block_the_event_loop(app_client, seek):
    import asyncio

    from app.agent import tools

    seek(5400)
    ticks = 0

    async def ticker():
        nonlocal ticks
        while True:
            await asyncio.sleep(0.005)
            ticks += 1

    task = asyncio.create_task(ticker())
    await asyncio.sleep(0)
    tools.ctx().store.__dict__.pop("_advisor_cache", None)  # force the slow (cold) path
    await tools.get_bench_view(MATCH, TEAM, 4300)
    task.cancel()
    assert ticks >= 3


def test_vacant_slot_is_not_described_as_no_alert():
    from app.services.bench import vacant_text

    text = vacant_text("RB", "Jérémy Doku")
    assert "RB" in text and "No defender is being beaten" not in text


def test_stale_importance_file_is_ignored(tmp_path):
    import json

    from app.services.bench import load_importance

    f = tmp_path / "imp.json"
    base = {"method": "m", "n": 1, "auc": 0.7, "caveat": "c",
            "ranked": [{"var_id": "x", "name": "x", "family": "PHY", "importance": 1.0, "rank": 1}]}  # fmt: skip
    f.write_text(json.dumps(base | {"model_version": "duel-v0"}))
    items, note = load_importance(f)
    assert items == [] and "stale" in note


def test_briefing_mentions_a_booked_tormentor(app_client, seek):
    seek(5400)
    v = bench(app_client, ALERT_SEC)
    store = app_client.app.state.store
    booked = any(
        e.event_type == "card" and e.player_id == "P-MCI-11" and e.event_sec <= ALERT_SEC
        for e in store.events(MATCH)
    )
    assert ("Jérémy Doku is on a yellow" in v["briefing_seed"]) is booked


def test_cached_first_fire_matches_a_fresh_scan(app_client):
    from app.services.bench import _first_fire
    from app.services.matchups import first_trigger

    store = app_client.app.state.store
    events, rosters = store.events(MATCH), store.rosters(MATCH)
    for asof in (ALERT_SEC - 1, ALERT_SEC, 4300, 5400):
        fresh = first_trigger([e for e in events if e.event_sec <= asof], rosters, TEAM, asof)
        cached = _first_fire(store, MATCH, TEAM, asof)
        assert cached[0] == fresh[0]
        assert [h.model_dump() for h in cached[1]] == [h.model_dump() for h in fresh[1]]


def test_bench_carries_the_league_reference_line(app_client, seek):
    from app.services.matchups import LEAGUE_DEF_WIN

    seek(5400)
    assert bench(app_client, ALERT_SEC)["league_def_win"] == LEAGUE_DEF_WIN

"""GET /api/matches/{id}/bench (Task 9): one payload for the assistant-coach page."""

import pytest

MATCH, TEAM = "SIM-001", "T-LIV"
ALERT_SEC = 3714  # first hot-duel trigger in the regenerated demo (docs/schema.md §11)


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
    assert v["executed_option_rank_at_alert"] is None or v["executed_option_rank_at_alert"] >= 1
    assert v["ledger"]["defender_ids"] == ["P-LIV-30", "P-LIV-08"]


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

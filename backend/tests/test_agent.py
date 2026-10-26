import pytest

from app.agent import rules, tools
from app.agent.ask import AskRequest, ask_rules

MATCH = "SIM-001"
ALERT_SEC = 4020  # after the 61.9' hot-duel trigger (3714 s), before the 70' swap


@pytest.fixture(scope="module")
def client(app_client):
    app_client.post(f"/api/matches/{MATCH}/replay", json={"action": "seek", "value": ALERT_SEC})
    return app_client


async def test_tools_never_see_past_replay_clock(client):
    state = await tools.get_match_state(MATCH, asof_sec=5000)
    assert state["asof_sec"] == ALERT_SEC


async def test_substitution_evaluation_has_keep_swap_and_sub(client):
    ev = await tools.evaluate_substitutions(MATCH, "T-LIV", 4080)
    assert ev["asof_sec"] == ALERT_SEC  # clamped to the replay clock
    kinds = [o["option_type"] for o in ev["options"]]
    assert kinds.count("keep") == 1 and "substitution" in kinds and "position_swap" in kinds
    assert {o["team_id"] for o in ev["options"]} == {"T-LIV"}
    assert all(o["supporting_event_ids"] for o in ev["options"])
    assert ev["hot_duel"]["defender_slot"] == "RB" and ev["hot_duel"]["attacker_id"] == "P-MCI-11"
    assert ev["ledger"]["duels"] >= 8 and ev["ledger"]["points"]
    swap = next(o for o in ev["options"] if o["option_type"] == "position_swap")
    assert swap["incoming_name"] == "Dominik Szoboszlai"
    assert swap["outgoing_name"] == "Jeremie Frimpong"
    # head-to-head is reported separately with its n, never blended into the score
    h2h = ev["head_to_head"]["P-LIV-08"]
    assert set(h2h) >= {"prior_meetings", "n"}


async def test_evaluation_before_alert_is_keep_only(client):
    ev = await tools.evaluate_substitutions(MATCH, "T-LIV", 1200)
    assert [o["option_type"] for o in ev["options"]] == ["keep"]
    assert ev["hot_duel"] is None and ev["ledger"] is None


async def test_get_duel_ledger_tool_clamped_to_clock(client):
    led = await tools.get_duel_ledger(MATCH, "P-MCI-11", "RB", "T-LIV", asof_sec=5000)
    assert led["asof_sec"] == ALERT_SEC
    assert led["points"] and all(p["sec"] <= ALERT_SEC for p in led["points"])
    assert led["defender_ids"] == ["P-LIV-30"]


async def test_insight_candidates_name_the_hot_duel(client):
    cands = await tools.get_insight_candidates(MATCH, since_sec=0)
    alert = next(c for c in cands["candidates"] if c["kind"] == "tactical_alert")
    assert alert["facts"]["attacker"] == "Jérémy Doku"
    assert alert["facts"]["defender"] == "Jeremie Frimpong"
    assert alert["asof_sec"] == 3714 and alert["evidence_event_ids"]
    fan, analyst = await rules.render(MATCH, alert)
    assert "Doku" in fan.headline and "RB" in analyst.headline


async def test_publish_insight_rejects_ungrounded_evidence(client):
    base = {
        "insight_id": "INS-TEST-1", "kind": "player_form", "match_id": MATCH,
        "asof_sec": ALERT_SEC, "audience": "fan", "headline": "h", "explanation": "e",
        "uncertainty": "u", "generator_version": "test",
    }  # fmt: skip
    with pytest.raises(tools.GroundingError, match="unknown"):
        await tools.publish_insight(base | {"evidence_event_ids": ["SIM-001-E9999"]})
    future = tools.ctx().store.events(MATCH)[-1].event_id
    with pytest.raises(tools.GroundingError, match="future"):
        await tools.publish_insight(base | {"evidence_event_ids": [future]})
    with pytest.raises(tools.GroundingError, match="contract"):
        await tools.publish_insight(base | {"evidence_event_ids": []})


async def test_rules_render_fan_and_analyst_variants_from_same_evidence(client):
    cands = await tools.get_insight_candidates(MATCH, since_sec=0)
    sub = next(c for c in cands["candidates"] if c["kind"] == "substitution_opportunity")
    fan, analyst = await rules.render(MATCH, sub)
    assert fan.audience == "fan" and analyst.audience == "analyst"
    assert fan.evidence_event_ids == analyst.evidence_event_ids
    assert fan.recommendation_id and fan.synthetic


async def test_rules_answer_mentions_keep(client):
    res = await ask_rules(AskRequest(match_id=MATCH, question="Should Liverpool make a change?"))
    assert "KEEP" in res.answer and res.evidence_event_ids


def test_briefing_rules_fallback_cites_evidence(client, monkeypatch):
    from types import SimpleNamespace

    from app import api

    monkeypatch.setattr(api, "get_settings", lambda: SimpleNamespace(agent_provider="rules"))
    r = client.post("/api/agent/ask", json={"match_id": MATCH, "question": "", "mode": "briefing",
                                           "team_id": "T-LIV"})  # fmt: skip
    assert r.status_code == 200, r.text
    res = r.json()
    assert res["provider"].startswith("rules")
    assert "KEEP" in res["answer"] and "simulated" in res["answer"]
    known = {e.event_id: e.event_sec for e in tools.ctx().store.events(MATCH)}
    assert res["evidence_event_ids"]
    assert all(i in known and known[i] <= ALERT_SEC for i in res["evidence_event_ids"])


def test_briefing_follows_the_scrubbed_second(client, monkeypatch):
    from types import SimpleNamespace

    from app import api

    monkeypatch.setattr(api, "get_settings", lambda: SimpleNamespace(agent_provider="rules"))
    client.post(f"/api/matches/{MATCH}/replay", json={"action": "seek", "value": 5400})
    try:
        r = client.post("/api/agent/ask", json={"match_id": MATCH, "mode": "briefing",
                                               "team_id": "T-LIV", "asof_sec": 3714,
                                               "chosen": "keep"})  # fmt: skip
        res = r.json()
    finally:
        client.post(f"/api/matches/{MATCH}/replay", json={"action": "seek", "value": ALERT_SEC})
    secs = {e.event_id: e.event_sec for e in tools.ctx().store.events(MATCH)}
    assert "62'" in res["answer"] and "Since the 70'" not in res["answer"]
    assert all(secs[i] <= 3714 for i in res["evidence_event_ids"])

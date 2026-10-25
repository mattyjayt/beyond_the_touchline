import pytest

from app.agent import rules, tools
from app.agent.ask import AskRequest, ask_rules

MATCH = "SIM-001"
ALERT_SEC = 4020


@pytest.fixture(scope="module")
def client(app_client):
    app_client.post(f"/api/matches/{MATCH}/replay", json={"action": "seek", "value": ALERT_SEC})
    return app_client


async def test_tools_never_see_past_replay_clock(client):
    state = await tools.get_match_state(MATCH, asof_sec=5000)
    assert state["asof_sec"] == ALERT_SEC


async def test_substitution_evaluation_has_keep_and_storyline_options(client):
    ev = await tools.evaluate_substitutions(MATCH, "T-ARS")
    kinds = [o["option_type"] for o in ev["options"]]
    assert "keep" in kinds and "substitution" in kinds
    assert ev["outgoing_candidate"]["player_id"] == "P-ARS-07"  # Saka struggling (scripted)
    incoming = {o["incoming_player_id"] for o in ev["options"]}
    assert incoming & {"P-ARS-56", "P-ARS-20"}
    assert all(o["supporting_event_ids"] for o in ev["options"])


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
    res = await ask_rules(AskRequest(match_id=MATCH, question="Should Arsenal make a change?"))
    assert "KEEP" in res.answer and res.evidence_event_ids

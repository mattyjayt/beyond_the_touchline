"""C5: the demo's calibration history and scripted elements are disclosed, in docs and on the page."""

import re
from pathlib import Path

DOCS = Path(__file__).resolve().parents[2] / "docs" / "schema.md"


def _section_11() -> str:
    text = DOCS.read_text()
    return text[text.index("## 11.") :]


def test_schema_discloses_every_demo_seed_and_recalibration():
    s11 = _section_11()
    for seed in ("2029", "2027", "2036", "2055"):
        assert seed in s11, seed
    assert re.search(r"30% .*42%", s11)  # the first seed's swap underdelivered
    assert "pinned" in s11 and "68" in s11


def test_bench_view_carries_the_disclosure(app_client):
    v = app_client.get("/api/matches/SIM-001/bench", params={"team_id": "T-LIV"}).json()
    d = v["disclosure"]
    assert "pinned" in d and "scripted" in d and "+0.6" in d

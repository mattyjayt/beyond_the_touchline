"""Variable catalogue (spec §5): every matchup variable the product knows about.

Two kinds of rows:
- our own variables (``phy.``, ``pri.``, ``ctx.``, ``duel.``, ``his.``, ``evt.``, ``rat.``):
  what the simulator, the advisor or the live services can measure. ``engine_causal`` marks
  inputs the duel model actually uses; only those are ranked by the study.
- the research report's 108 rows (``ref.``), parsed from
  ``reports/Football matchup variables catalogue.md``: descriptive only, never ranked.

Real-world ranges and references always come from the report. Everything simulated is labelled.

``python -m app.analysis.catalogue`` writes ``docs/variable_catalogue.md``.
"""

import re
from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[3]
REPORT = ROOT / "reports" / "Football matchup variables catalogue.md"
DOC = ROOT / "docs" / "variable_catalogue.md"

Family = Literal["PHY", "PRI", "EVT", "HIS", "RAT", "CTX", "DUEL"]
Source = Literal["physical_synthetic", "prior", "event", "historical", "rating", "context"]
FAMILIES: tuple[Family, ...] = ("PHY", "PRI", "EVT", "HIS", "RAT", "CTX", "DUEL")

# report section letter -> (family, source) for the descriptive research rows
_SECTION: dict[str, tuple[Family, Source]] = {
    "A": ("PHY", "physical_synthetic"),
    "B": ("PHY", "physical_synthetic"),
    "C": ("CTX", "context"),
    "D": ("DUEL", "context"),
    "E": ("EVT", "event"),
    "F": ("EVT", "event"),
    "G": ("EVT", "event"),
    "H": ("CTX", "context"),
}


@dataclass(frozen=True)
class Variable:
    id: str
    family: Family
    name: str
    unit: str
    source: Source
    window: str
    engine_causal: bool
    advisor_uses: bool
    real_range: str
    ref: str


@cache
def research_rows(path: Path = REPORT) -> dict[int, dict[str, str]]:
    """Report row number -> {section, name, unit, range, tag, source} from its tables."""
    rows: dict[int, dict[str, str]] = {}
    section = ""
    for line in path.read_text().splitlines():
        if m := re.match(r"### ([A-H])\. ", line):
            section = m[1]
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if section and len(cells) == 6 and cells[0].isdigit():
            num, name, unit, rng, tag, src = cells
            rows[int(num)] = {"section": section, "name": name, "unit": unit, "range": rng,
                              "tag": tag, "source": src}  # fmt: skip
    return rows


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")[:40]


def _ref(*nums: int) -> tuple[str, str]:
    """(real_range, ref) quoted from report rows."""
    rows = research_rows()
    rng = "; ".join(f"#{n}: {rows[n]['range']}" for n in nums if n in rows)
    return rng, ", ".join(f"report #{n}" for n in nums if n in rows)


# (id, family, name, unit, source, window, engine_causal, advisor_uses, report rows)
_OWN: list[tuple[str, Family, str, str, Source, str, bool, bool, tuple[int, ...]]] = [
    # physical profile (synthetic, real units are the source)
    ("phy.att_top_speed_kmh", "PHY", "Attacker top speed", "km/h", "physical_synthetic", "profile", True, True, (1, 3)),
    ("phy.def_top_speed_kmh", "PHY", "Defender top speed", "km/h", "physical_synthetic", "profile", True, True, (1, 4)),
    ("phy.speed_kmh_diff", "PHY", "Top speed gap (defender - attacker)", "km/h", "physical_synthetic", "profile", True, True, (1, 4)),
    ("phy.att_accel_ms2", "PHY", "Attacker max acceleration", "m/s²", "physical_synthetic", "profile", True, True, (15, 17)),
    ("phy.def_accel_ms2", "PHY", "Defender max acceleration", "m/s²", "physical_synthetic", "profile", True, True, (15, 18)),
    ("phy.accel_idx_diff", "PHY", "Acceleration index gap (attacker - defender)", "index", "physical_synthetic", "profile", True, True, (41, 15)),
    ("phy.att_time_0_5m_s", "PHY", "Attacker time to 5 m", "s", "physical_synthetic", "profile", True, True, (23,)),
    ("phy.def_time_0_5m_s", "PHY", "Defender time to 5 m", "s", "physical_synthetic", "profile", True, True, (23,)),
    ("phy.att_agility_idx", "PHY", "Attacker agility", "index", "physical_synthetic", "profile", True, False, (26, 27)),
    ("phy.def_agility_idx", "PHY", "Defender agility", "index", "physical_synthetic", "profile", True, False, (26, 28)),
    ("phy.agility_idx_diff", "PHY", "Agility gap (attacker - defender)", "index", "physical_synthetic", "profile", True, False, (26,)),
    ("phy.att_stamina_idx", "PHY", "Attacker stamina", "index", "physical_synthetic", "profile", True, False, (31,)),
    ("phy.def_stamina_idx", "PHY", "Defender stamina", "index", "physical_synthetic", "profile", True, True, (31,)),
    ("phy.def_stance_idx", "PHY", "Defender side-on tendency", "index", "physical_synthetic", "profile", True, True, (45,)),
    ("phy.att_height_cm", "PHY", "Attacker height", "cm", "physical_synthetic", "profile", False, False, ()),
    ("phy.def_height_cm", "PHY", "Defender height", "cm", "physical_synthetic", "profile", False, False, ()),
    # ability priors (synthetic)
    ("pri.att_dribbling", "PRI", "Attacker dribbling prior", "0-100", "prior", "season", True, False, (56,)),
    ("pri.def_defending", "PRI", "Defender defending prior", "0-100", "prior", "season", True, True, (74, 76)),
    ("pri.tech_gap", "PRI", "Dribbling minus defending prior", "0-100", "prior", "season", True, False, (56, 74)),
    ("pri.att_passing", "PRI", "Attacker passing prior", "0-100", "prior", "season", False, True, ()),
    ("pri.att_finishing", "PRI", "Attacker finishing prior", "0-100", "prior", "season", False, True, (67,)),
    ("pri.att_physical", "PRI", "Attacker physical prior", "0-100", "prior", "season", False, False, ()),
    ("pri.def_physical", "PRI", "Defender physical prior", "0-100", "prior", "season", False, False, ()),
    ("pri.def_passing", "PRI", "Defender passing prior", "0-100", "prior", "season", False, True, ()),
    # duel context
    ("ctx.isolated", "CTX", "Defender isolated (no team-mate within 15u)", "flag", "context", "duel", True, True, (52, 51)),
    ("ctx.cover_near", "CTX", "Covering team-mate within 10u", "flag", "context", "duel", True, True, (51, 50)),
    ("ctx.transition", "CTX", "Transition (possession < 8 s old)", "flag", "context", "duel", True, False, (104,)),
    ("ctx.defender_on_yellow", "CTX", "Defender on a yellow card", "flag", "context", "duel", True, True, (97,)),
    ("ctx.touch_dist", "CTX", "Distance to nearest touchline", "units", "context", "duel", True, False, (48,)),
    ("ctx.stance_draw", "CTX", "Per-duel stance (side-on = 1)", "0-1", "context", "duel", True, True, (45,)),
    ("ctx.att_minutes_on", "CTX", "Attacker minutes on the pitch", "min", "context", "duel", True, True, (30,)),
    ("ctx.def_minutes_on", "CTX", "Defender minutes on the pitch", "min", "context", "duel", True, True, (30, 38)),
    ("ctx.att_fatigue_mult", "CTX", "Attacker fatigue multiplier", "ratio", "context", "duel", True, False, (31, 33)),
    ("ctx.def_fatigue_mult", "CTX", "Defender fatigue multiplier", "ratio", "context", "duel", True, True, (31, 33)),
    ("ctx.goal_diff", "CTX", "Goal difference for the defending team", "goals", "context", "match", False, True, (95,)),
    ("ctx.minute", "CTX", "Match minute", "min", "context", "match", False, True, (96,)),
    ("ctx.subs_left", "CTX", "Substitutions left", "count", "context", "match", False, True, ()),
    ("ctx.out_of_position", "CTX", "Defender out of position", "flag", "context", "match", False, True, (102,)),
    # duel model terms (stored on every take-on event)
    ("duel.tech", "DUEL", "Technique term", "logit pts", "context", "duel", True, False, ()),
    ("duel.burst", "DUEL", "First-step burst term", "logit pts", "context", "duel", True, True, (41, 12)),
    ("duel.agil", "DUEL", "Agility term", "logit pts", "context", "duel", True, False, (26,)),
    ("duel.ctx", "DUEL", "Context term", "logit pts", "context", "duel", True, False, (50, 48)),
    ("duel.p_recover", "DUEL", "Recovery chance once beaten", "0-1", "context", "duel", False, False, (24,)),
    # history (prior simulated matches) - descriptive
    ("his.att_take_on_pct_l5", "HIS", "Attacker take-on success, last 5", "%", "historical", "l5", False, False, (56,)),
    ("his.att_take_ons_p90_l5", "HIS", "Attacker take-on attempts p90, last 5", "p90", "historical", "l5", False, False, (55,)),
    ("his.def_duel_win_pct_l5", "HIS", "Defender 1v1 win %, last 5", "%", "historical", "l5", False, False, (74, 76)),
    ("his.def_beaten_p90_l5", "HIS", "Defender dribbled past p90, last 5", "p90", "historical", "l5", False, False, (75,)),
    ("his.att_rating_l5", "HIS", "Attacker rating, last 5", "0-10", "historical", "l5", False, True, ()),
    ("his.def_rating_l5", "HIS", "Defender rating, last 5", "0-10", "historical", "l5", False, True, ()),
    ("his.def_n_at_slot", "HIS", "Prior matches at the slot", "count", "historical", "season", False, True, (102,)),
    ("his.h2h_take_ons", "HIS", "Head-to-head take-ons in prior meetings", "count", "historical", "season", False, True, ()),
    # live events - descriptive
    ("evt.take_on_won_20m", "EVT", "Attacker take-ons won vs the slot", "count", "event", "20m", False, True, (57,)),
    ("evt.take_on_att_20m", "EVT", "Attacker take-ons vs the slot", "count", "event", "20m", False, True, (55,)),
    ("evt.def_beaten_20m", "EVT", "Defender beaten without recovery", "count", "event", "20m", False, True, (75,)),
    ("evt.def_win_pct_20m", "EVT", "Defender duel win %", "%", "event", "20m", False, True, (74,)),
    ("evt.channel_shots_match", "EVT", "Shots from the attacker's channel", "count", "event", "match", False, True, (67,)),
    ("evt.channel_xg_match", "EVT", "xG from the attacker's channel", "xG", "event", "match", False, True, (67,)),
    ("evt.def_recoveries_match", "EVT", "Recovery tackles after being beaten", "count", "event", "match", False, True, ()),
    ("evt.def_fouls_match", "EVT", "Fouls by the defender on the attacker", "count", "event", "match", False, True, ()),
    # ratings - descriptive
    ("rat.att_live", "RAT", "Attacker live rating", "0-10", "rating", "match", False, False, ()),
    ("rat.def_live", "RAT", "Defender live rating", "0-10", "rating", "match", False, True, ()),
    ("rat.def_form_delta", "RAT", "Defender live minus expected rating", "0-10", "rating", "match", False, True, ()),
    ("rat.def_duel_swing", "RAT", "Rating swing from the duel ledger", "0-10", "rating", "match", False, True, ()),
]  # fmt: skip

# Variables an isolated sampled duel can supply (keys of duel_study.build_features).
STUDY_IDS: tuple[str, ...] = tuple(
    v[0] for v in _OWN if v[0].split(".")[0] in ("phy", "pri", "duel")
    or v[0] in {"ctx.isolated", "ctx.cover_near", "ctx.transition", "ctx.defender_on_yellow",
                "ctx.touch_dist", "ctx.stance_draw", "ctx.att_minutes_on", "ctx.def_minutes_on",
                "ctx.att_fatigue_mult", "ctx.def_fatigue_mult"}
)  # fmt: skip


def _build() -> list[Variable]:
    out = []
    for vid, fam, name, unit, src, window, causal, uses, refs in _OWN:
        rng, ref = _ref(*refs) if refs else ("simulated only", "")
        out.append(Variable(vid, fam, name, unit, src, window, causal, uses, rng, ref))
    for num, row in sorted(research_rows().items()):
        fam, src = _SECTION[row["section"]]
        out.append(Variable(
            id=f"ref.{row['section'].lower()}{num:03d}_{_slug(row['name'])}", family=fam,
            name=row["name"], unit=row["unit"], source=src, window="research",
            engine_causal=False, advisor_uses=False, real_range=row["range"],
            ref=f"report #{num} ({row['tag']}): {row['source']}",
        ))  # fmt: skip
    return out


VARIABLES: list[Variable] = _build()


def _cell(text: str) -> str:
    return text.replace("|", "/").replace("\n", " ")


def render_markdown() -> str:
    head = [
        "# Variable catalogue",
        "",
        (
            "> Generated by `uv run python -m app.analysis.catalogue`. Everything simulated is "
            "labelled; real-world ranges and references come from "
            "`reports/Football matchup variables catalogue.md`. Only `engine_causal` variables are "
            "ranked by the duel study; the rest are descriptive."
        ),
        "",
        f"{len(VARIABLES)} variables · families: "
        + ", ".join(f"{f} {sum(v.family == f for v in VARIABLES)}" for f in FAMILIES),
        "",
        (
            "| id | family | name | unit | source | window | engine causal | advisor uses | "
            "real range | ref |"
        ),
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    rows = [
        f"| `{v.id}` | {v.family} | {_cell(v.name)} | {_cell(v.unit)} | {v.source} | {v.window} "
        f"| {'yes' if v.engine_causal else ''} | {'yes' if v.advisor_uses else ''} "
        f"| {_cell(v.real_range)} | {_cell(v.ref)} |"
        for v in VARIABLES
    ]
    return "\n".join(head + rows) + "\n"


def main() -> None:
    DOC.write_text(render_markdown())
    print(f"wrote {DOC.relative_to(ROOT)} ({len(VARIABLES)} variables)")


if __name__ == "__main__":
    main()

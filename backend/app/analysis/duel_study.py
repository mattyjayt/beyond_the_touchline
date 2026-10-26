"""Duel study (spec §4): which variables drive the simulator's 1v1 outcomes?

Methodology demo: importance mirrors the generator (the outcome is drawn from the same
``duel_prob`` the engine uses), so this shows the method, not football truth.

- Sample attacker/defender pairs from every squad (attackers ATT/MID, defenders DEF/MID) and
  contexts uniform over the ``DuelContext`` fields; draw "attacker beats defender" as
  Bernoulli(p_beat).
- Standardise the study features and fit ``LogisticRegression`` on a 75/25 split.
- Rank only ``engine_causal`` variables by permutation importance on the test split (AUC drop),
  with mutual information as a cross-check column.

``python -m app.analysis.duel_study --n 40000`` writes ``backend/data/variable_importance.json``
and ``docs/variable_importance.md``.
"""

import argparse
import json
import random
from dataclasses import dataclass, field

import numpy as np
from sklearn.feature_selection import mutual_info_classif
from sklearn.inspection import permutation_importance
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from app.analysis.catalogue import ROOT, STUDY_IDS, VARIABLES
from app.config import get_settings
from app.models import ROLE_GROUP, ImportanceItem, Player
from app.sim.duel import MODEL_VERSION, DuelContext, duel_prob, fatigue
from app.sim.squads import load_reference

JSON_OUT = ROOT / "backend" / "data" / "variable_importance.json"
MD_OUT = ROOT / "docs" / "variable_importance.md"
CAVEAT = (
    f"methodology demo: importance mirrors the generator (`{MODEL_VERSION}`); not football truth"
)
METHOD = "standardised logistic regression · permutation importance (ROC AUC drop, 5 repeats)"
TOP_N = 25

_BY_ID = {v.id: v for v in VARIABLES}
CAUSAL_IDS: tuple[str, ...] = tuple(i for i in STUDY_IDS if _BY_ID[i].engine_causal)


@dataclass
class StudyResult:
    n: int
    seed: int
    auc: float
    method: str
    ranked: list[ImportanceItem]  # top engine-causal variables
    mutual_info: dict[str, float] = field(default_factory=dict)
    not_ranked: list[str] = field(default_factory=list)  # descriptive study variables


def build_features(att: Player, dfn: Player, c: DuelContext, stance: float) -> dict[str, float]:
    """Study features for one duel; keys are the catalogue's STUDY_IDS."""
    a, d = att.physical, dfn.physical
    ap, dp = att.priors, dfn.priors
    t = duel_prob(att, dfn, c, stance)
    f = {
        "phy.att_top_speed_kmh": a.top_speed_kmh,
        "phy.def_top_speed_kmh": d.top_speed_kmh,
        "phy.speed_kmh_diff": d.top_speed_kmh - a.top_speed_kmh,
        "phy.att_accel_ms2": a.accel_ms2,
        "phy.def_accel_ms2": d.accel_ms2,
        "phy.accel_idx_diff": a.accel_idx - d.accel_idx,
        "phy.att_time_0_5m_s": a.time_0_5m_s,
        "phy.def_time_0_5m_s": d.time_0_5m_s,
        "phy.att_agility_idx": a.agility_idx,
        "phy.def_agility_idx": d.agility_idx,
        "phy.agility_idx_diff": a.agility_idx - d.agility_idx,
        "phy.att_stamina_idx": a.stamina_idx,
        "phy.def_stamina_idx": d.stamina_idx,
        "phy.def_stance_idx": d.stance_idx,
        "phy.att_height_cm": a.height_cm,
        "phy.def_height_cm": d.height_cm,
        "pri.att_dribbling": ap.dribbling,
        "pri.def_defending": dp.defending,
        "pri.tech_gap": ap.dribbling - dp.defending,
        "pri.att_passing": ap.passing,
        "pri.att_finishing": ap.finishing,
        "pri.att_physical": ap.physical,
        "pri.def_physical": dp.physical,
        "pri.def_passing": dp.passing,
        "ctx.isolated": float(c.isolated),
        "ctx.cover_near": float(c.cover_near),
        "ctx.transition": float(c.transition),
        "ctx.defender_on_yellow": float(c.defender_on_yellow),
        "ctx.touch_dist": c.touch,
        "ctx.stance_draw": stance,
        "ctx.att_minutes_on": c.att_minutes_on,
        "ctx.def_minutes_on": c.def_minutes_on,
        "ctx.att_fatigue_mult": fatigue(c.att_minutes_on, a.stamina_idx),
        "ctx.def_fatigue_mult": fatigue(c.def_minutes_on, d.stamina_idx),
        "duel.tech": t.tech,
        "duel.burst": t.burst,
        "duel.agil": t.agil,
        "duel.ctx": t.ctx,
        "duel.p_recover": t.p_recover,
    }
    return {k: float(f[k]) for k in STUDY_IDS}


def sample(seed: int, n: int) -> tuple[np.ndarray, np.ndarray]:
    """``n`` sampled duels: (features in STUDY_IDS order, beaten 0/1)."""
    rng = random.Random(f"duel-study-{seed}")
    _, players = load_reference(seed)
    usable = [p for p in players if p.physical and p.priors]
    attackers = [p for p in usable if ROLE_GROUP[p.primary_position] in ("ATT", "MID")]
    defenders = [p for p in usable if ROLE_GROUP[p.primary_position] in ("DEF", "MID")]
    X = np.empty((n, len(STUDY_IDS)))
    y = np.empty(n, dtype=int)
    for i in range(n):
        att, dfn = rng.choice(attackers), rng.choice(defenders)
        while dfn.team_id == att.team_id:
            dfn = rng.choice(defenders)
        c = DuelContext(
            isolated=rng.random() < 0.5, transition=rng.random() < 0.5,
            defender_on_yellow=rng.random() < 0.5, cover_near=rng.random() < 0.5,
            touch=rng.uniform(0, 50), att_minutes_on=rng.uniform(0, 95),
            def_minutes_on=rng.uniform(0, 95),
        )  # fmt: skip
        stance = min(1.0, max(0.0, rng.gauss(dfn.physical.stance_idx / 100, 0.15)))
        feats = build_features(att, dfn, c, stance)
        X[i] = [feats[k] for k in STUDY_IDS]
        y[i] = rng.random() < duel_prob(att, dfn, c, stance).p_beat
    return X, y


def run_study(seed: int, n: int) -> StudyResult:
    X, y = sample(seed, n)
    cols = [STUDY_IDS.index(k) for k in CAUSAL_IDS]
    Xc = X[:, cols]
    X_tr, X_te, y_tr, y_te = train_test_split(Xc, y, test_size=0.25, random_state=seed, stratify=y)
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    model.fit(X_tr, y_tr)
    auc = round(float(roc_auc_score(y_te, model.predict_proba(X_te)[:, 1])), 4)
    perm = permutation_importance(
        model, X_te, y_te, scoring="roc_auc", n_repeats=5, random_state=seed
    )
    mi = mutual_info_classif(X_te, y_te, random_state=seed)
    order = sorted(range(len(CAUSAL_IDS)), key=lambda j: (-perm.importances_mean[j], CAUSAL_IDS[j]))
    ranked = [
        ImportanceItem(
            var_id=CAUSAL_IDS[j],
            name=_BY_ID[CAUSAL_IDS[j]].name,
            family=_BY_ID[CAUSAL_IDS[j]].family,
            importance=round(float(perm.importances_mean[j]), 5),
            rank=r,
        )
        for r, j in enumerate(order[:TOP_N], start=1)
    ]
    return StudyResult(
        n=n, seed=seed, auc=auc, method=METHOD, ranked=ranked,
        mutual_info={CAUSAL_IDS[j]: round(float(mi[j]), 5) for j in range(len(CAUSAL_IDS))},
        not_ranked=[i for i in STUDY_IDS if i not in CAUSAL_IDS],
    )  # fmt: skip


def write(result: StudyResult) -> None:
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps({
        "caveat": CAVEAT, "method": result.method, "seed": result.seed, "n": result.n,
        "auc": result.auc, "model_version": MODEL_VERSION,
        "ranked": [r.model_dump() for r in result.ranked],
        "mutual_info": result.mutual_info, "not_ranked": result.not_ranked, "synthetic": True,
    }, indent=2))  # fmt: skip
    lines = [
        "# Variable importance (duel study)",
        "",
        f"> **{CAVEAT}.** Generated by `uv run python -m app.analysis.duel_study --n {result.n}`.",
        "",
        f"- Method: {result.method}; mutual information as a cross-check.",
        f"- Seed {result.seed} · n = {result.n} simulated duels · test AUC {result.auc}.",
        (
            "- Correlated variables share credit: a duel term (e.g. `duel.ctx`) absorbs much of its "
            "inputs' importance (e.g. stance), so read families together, not single ranks."
        ),
        "- Only engine-causal variables are ranked. Descriptive study variables (not ranked): "
        + ", ".join(f"`{i}`" for i in result.not_ranked)
        + ".",
        "",
        "| rank | variable | family | permutation importance (AUC drop) | mutual info |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| {r.rank} | `{r.var_id}` {r.name} | {r.family} | {r.importance:.5f} "
        f"| {result.mutual_info[r.var_id]:.5f} |"
        for r in result.ranked
    ]
    MD_OUT.write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=40000)
    ap.add_argument("--seed", type=int, default=get_settings().sim_seed)
    args = ap.parse_args()
    result = run_study(args.seed, args.n)
    write(result)
    print(f"duel study  n={result.n} seed={result.seed} AUC={result.auc}  ({CAVEAT})")
    for r in result.ranked:
        print(f"  {r.rank:>2}. {r.var_id:<28} {r.importance:.5f}")


if __name__ == "__main__":
    main()

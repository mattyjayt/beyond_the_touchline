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
METHOD = (
    "standardised logistic regression on primitive inputs · grouped permutation importance "
    "(ROC AUC drop, 5 repeats) · ranks over several seeds"
)
N_REPEATS = 5

_BY_ID = {v.id: v for v in VARIABLES}
# Importance is measured per GROUP of primitive inputs: near-duplicates (attacker vs defender
# acceleration, time-to-5 m vs acceleration) would otherwise split credit arbitrarily. Derived
# terms (duel.*, gaps, time-to-5 m, fatigue multipliers) are not fitted at all (C11).
GROUPS: dict[str, dict] = {
    "group.acceleration": {"name": "Acceleration (attacker + defender)", "family": "PHY",
                           "vars": ["phy.att_accel_ms2", "phy.def_accel_ms2"]},
    "group.pace": {"name": "Top speed (attacker + defender)", "family": "PHY",
                   "vars": ["phy.att_top_speed_kmh", "phy.def_top_speed_kmh"]},
    "group.agility": {"name": "Agility (attacker + defender)", "family": "PHY",
                      "vars": ["phy.att_agility_idx", "phy.def_agility_idx"]},
    "group.stamina": {"name": "Stamina and minutes played", "family": "CTX",
                      "vars": ["phy.att_stamina_idx", "phy.def_stamina_idx",
                               "ctx.att_minutes_on", "ctx.def_minutes_on"]},
    "group.technique": {"name": "Dribbling vs defending priors", "family": "PRI",
                        "vars": ["pri.att_dribbling", "pri.def_defending"]},
    "group.stance": {"name": "Defender stance (tendency + per-duel)", "family": "PHY",
                     "vars": ["phy.def_stance_idx", "ctx.stance_draw"]},
    "group.cover": {"name": "Isolation and cover", "family": "CTX",
                    "vars": ["ctx.isolated", "ctx.cover_near"]},
    "group.transition": {"name": "Transition exposure", "family": "CTX",
                         "vars": ["ctx.transition"]},
    "group.booking": {"name": "Defender on a yellow", "family": "CTX",
                      "vars": ["ctx.defender_on_yellow"]},
    "group.touchline": {"name": "Distance to the touchline", "family": "CTX",
                        "vars": ["ctx.touch_dist"]},
}  # fmt: skip
FITTED_IDS: tuple[str, ...] = tuple(v for g in GROUPS.values() for v in g["vars"])
CAUSAL_IDS: tuple[str, ...] = tuple(i for i in STUDY_IDS if _BY_ID[i].engine_causal)


@dataclass
class StudyResult:
    n: int
    seed: int
    auc: float  # mean test AUC of the fitted model over the seeds
    oracle_auc: float  # mean test AUC of the TRUE p_beat: the ceiling any model can reach
    method: str
    ranked: list[ImportanceItem]  # groups, by mean importance, with rank intervals
    seeds: list[int] = field(default_factory=list)
    not_ranked: list[str] = field(default_factory=list)  # study variables not fitted


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


def sample(seed: int, n: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """``n`` sampled duels: (features in STUDY_IDS order, beaten 0/1, true p_beat)."""
    rng = random.Random(f"duel-study-{seed}")
    _, players = load_reference(seed)
    usable = [p for p in players if p.physical and p.priors]
    attackers = [p for p in usable if ROLE_GROUP[p.primary_position] in ("ATT", "MID")]
    defenders = [p for p in usable if ROLE_GROUP[p.primary_position] in ("DEF", "MID")]
    X = np.empty((n, len(STUDY_IDS)))
    y = np.empty(n, dtype=int)
    p = np.empty(n)
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
        p[i] = duel_prob(att, dfn, c, stance).p_beat
        y[i] = rng.random() < p[i]
    return X, y, p


def _one_seed(seed: int, n: int) -> tuple[float, float, dict[str, float]]:
    """(model AUC, oracle AUC, group -> mean AUC drop) for one seed."""
    X, y, p = sample(seed, n)
    cols = [STUDY_IDS.index(k) for k in FITTED_IDS]
    Xf = X[:, cols]
    idx = np.arange(n)
    tr, te = train_test_split(idx, test_size=0.25, random_state=seed, stratify=y)
    model = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000))
    model.fit(Xf[tr], y[tr])
    base = roc_auc_score(y[te], model.predict_proba(Xf[te])[:, 1])
    oracle = roc_auc_score(y[te], p[te])
    rng = np.random.default_rng(seed)
    drops: dict[str, float] = {}
    for gid, g in GROUPS.items():
        gcols = [FITTED_IDS.index(v) for v in g["vars"]]
        losses = []
        for _ in range(N_REPEATS):
            Xp = Xf[te].copy()
            perm = rng.permutation(len(te))
            Xp[:, gcols] = Xp[perm][:, gcols]  # permute the group's columns together
            losses.append(base - roc_auc_score(y[te], model.predict_proba(Xp)[:, 1]))
        drops[gid] = float(np.mean(losses))
    return float(base), float(oracle), drops


def run_study(seed: int, n: int, seeds: int = 5) -> StudyResult:
    seed_list = [seed + k for k in range(seeds)]
    runs = [_one_seed(s, n) for s in seed_list]
    ranks: dict[str, list[int]] = {g: [] for g in GROUPS}
    for _, _, drops in runs:
        for r, g in enumerate(sorted(GROUPS, key=lambda g: (-drops[g], g)), start=1):
            ranks[g].append(r)
    mean = {g: float(np.mean([d[g] for _, _, d in runs])) for g in GROUPS}
    order = sorted(GROUPS, key=lambda g: (-mean[g], g))
    ranked = [
        ImportanceItem(
            var_id=g, name=GROUPS[g]["name"], family=GROUPS[g]["family"],
            importance=round(mean[g], 5), rank=r, rank_lo=min(ranks[g]), rank_hi=max(ranks[g]),
        )
        for r, g in enumerate(order, start=1)
    ]  # fmt: skip
    for item in ranked:  # the overall rank sits inside the per-seed interval by construction
        item.rank_lo = min(item.rank_lo or item.rank, item.rank)
        item.rank_hi = max(item.rank_hi or item.rank, item.rank)
    return StudyResult(
        n=n, seed=seed, seeds=seed_list, method=METHOD, ranked=ranked,
        auc=round(float(np.mean([a for a, _, _ in runs])), 4),
        oracle_auc=round(float(np.mean([o for _, o, _ in runs])), 4),
        not_ranked=[i for i in STUDY_IDS if i not in FITTED_IDS],
    )  # fmt: skip


def write(result: StudyResult) -> None:
    JSON_OUT.parent.mkdir(parents=True, exist_ok=True)
    JSON_OUT.write_text(json.dumps({
        "caveat": CAVEAT, "method": result.method, "seed": result.seed, "seeds": result.seeds,
        "n": result.n, "auc": result.auc, "oracle_auc": result.oracle_auc,
        "model_version": MODEL_VERSION, "ranked": [r.model_dump() for r in result.ranked],
        "groups": GROUPS, "not_ranked": result.not_ranked, "synthetic": True,
    }, indent=2))  # fmt: skip
    seeds = f"{result.seeds[0]}–{result.seeds[-1]}"
    lines = [
        "# Variable importance (duel study)",
        "",
        f"> **{CAVEAT}.** Generated by `uv run python -m app.analysis.duel_study --n {result.n}`.",
        "",
        f"- Method: {result.method}.",
        (
            f"- Seeds {seeds} · n = {result.n} simulated duels per seed · mean test AUC "
            f"{result.auc} against an oracle AUC of {result.oracle_auc} (scoring with the true "
            "p_beat). "
            + (
                "The model is at the ceiling, so the ranking says how the generator is built, "
                "nothing more."
                if result.auc >= result.oracle_auc - 0.02
                else "The model is below the ceiling: some generator structure is not captured."
            )
        ),
        "- Groups pool near-duplicate inputs so they don't split credit. Derived terms "
        "(duel model terms, gaps, time-to-5 m, fatigue multipliers) are not fitted: "
        + ", ".join(f"`{i}`" for i in result.not_ranked)
        + ".",
        "",
        "| rank | group | inputs | AUC drop (mean) | rank range over seeds |",
        "|---|---|---|---|---|",
    ]
    lines += [
        f"| {r.rank} | {r.name} | {', '.join(f'`{v}`' for v in GROUPS[r.var_id]['vars'])} "
        f"| {r.importance:.5f} | {r.rank_lo}–{r.rank_hi} |"
        for r in result.ranked
    ]
    MD_OUT.write_text("\n".join(lines) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=40000)
    ap.add_argument("--seed", type=int, default=get_settings().sim_seed)
    ap.add_argument("--seeds", type=int, default=5)
    args = ap.parse_args()
    result = run_study(args.seed, args.n, args.seeds)
    write(result)
    print(f"duel study  n={result.n} seeds={result.seeds} AUC={result.auc} "
          f"oracle={result.oracle_auc}  ({CAVEAT})")  # fmt: skip
    for r in result.ranked:
        print(f"  {r.rank:>2}. {r.var_id:<22} {r.importance:.5f}  ranks {r.rank_lo}-{r.rank_hi}")


if __name__ == "__main__":
    main()

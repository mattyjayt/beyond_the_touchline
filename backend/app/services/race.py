"""Sprint race (spec 4): simulated 0-3 s distance curves from the physical profile.

After a fixed reaction time, speed follows v(t) = vmax * (1 - exp(-t / tau)) with
tau = vmax / accel (vmax in m/s). Distance is the closed-form integral. Simulator model,
uncalibrated: the UI animates these samples and never computes its own.
"""

import math

from app.models import Player, RaceCurve, RaceResult

LABEL = "Simulated sprint model from synthetic physical profiles; not measured data."


def _distance(t: float, vmax: float, tau: float, reaction_s: float) -> float:
    s = t - reaction_s
    if s <= 0:
        return 0.0
    return vmax * (s - tau * (1 - math.exp(-s / tau)))


def _t_at(dist: float, vmax: float, tau: float, reaction_s: float) -> float:
    lo, hi = reaction_s, reaction_s + 10.0
    for _ in range(60):  # bisection; distance is increasing after the reaction time
        mid = (lo + hi) / 2
        if _distance(mid, vmax, tau, reaction_s) < dist:
            lo = mid
        else:
            hi = mid
    return hi


def race(
    players: list[Player], horizon: float = 3.0, dt: float = 0.05, reaction_s: float = 0.25
) -> RaceResult:
    """Curves for ``players``; gaps are metres relative to the first player."""
    steps = round(horizon / dt)
    ts = [round(i * dt, 3) for i in range(steps + 1)]
    curves: list[RaceCurve] = []
    for p in players:
        if p.physical is None:
            raise ValueError(f"{p.player_id} has no physical profile")
        vmax = p.physical.top_speed_kmh / 3.6
        tau = vmax / p.physical.accel_ms2

        def dist(t: float, vmax: float = vmax, tau: float = tau) -> float:
            return _distance(t, vmax, tau, reaction_s)

        curves.append(
            RaceCurve(
                player_id=p.player_id,
                name=p.display_name,
                t=ts,
                d=[round(dist(t), 3) for t in ts],
                t5m=round(_t_at(5.0, vmax, tau, reaction_s), 3),
                d1s=round(dist(1.0), 3),
                d2s=round(dist(2.0), 3),
            )
        )
    ref = curves[0] if curves else None
    gap1s = {c.player_id: round(c.d1s - ref.d1s, 2) for c in curves} if ref else {}
    gap2s = {c.player_id: round(c.d2s - ref.d2s, 2) for c in curves} if ref else {}
    return RaceResult(curves=curves, gap1s=gap1s, gap2s=gap2s, reaction_s=reaction_s, label=LABEL)

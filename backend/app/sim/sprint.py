"""Sprint kinematics shared by the duel model, the sprint race and the physical profile.

After a fixed reaction time, speed follows v(t) = vmax * (1 - exp(-t / tau)) with
tau = vmax / A0 (vmax in m/s, A0 = maximal starting acceleration in m/s2), the standard
sprint-acceleration model. Distance is the closed-form integral. Simulator model, uncalibrated.
"""

import math

REACTION_S = 0.25


def distance(t: float, vmax_kmh: float, a0: float, reaction_s: float = REACTION_S) -> float:
    """Metres covered ``t`` seconds after the trigger (0 during the reaction time)."""
    s = t - reaction_s
    if s <= 0:
        return 0.0
    vmax = vmax_kmh / 3.6
    tau = vmax / a0
    return vmax * (s - tau * (1 - math.exp(-s / tau)))


def time_to(dist: float, vmax_kmh: float, a0: float, reaction_s: float = REACTION_S) -> float:
    """Seconds to cover ``dist`` metres, reaction included (bisection; distance increases)."""
    lo, hi = reaction_s, reaction_s + 10.0
    for _ in range(60):
        mid = (lo + hi) / 2
        if distance(mid, vmax_kmh, a0, reaction_s) < dist:
            lo = mid
        else:
            hi = mid
    return hi

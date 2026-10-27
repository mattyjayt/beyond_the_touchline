"""Sprint race (spec 4): simulated 0-3 s distance curves from the physical profile.

Kinematics live in ``app.sim.sprint`` (shared with the duel model and the physical profile).
Simulator model, uncalibrated: the UI animates these samples and never computes its own.
"""

from app.models import Player, RaceCurve, RaceResult
from app.sim import sprint

LABEL = "Simulated sprint model from synthetic physical profiles; not measured data."


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
        kmh, a0 = p.physical.top_speed_kmh, p.physical.accel_ms2

        def dist(t: float, kmh: float = kmh, a0: float = a0) -> float:
            return sprint.distance(t, kmh, a0, reaction_s)

        curves.append(
            RaceCurve(
                player_id=p.player_id,
                name=p.display_name,
                t=ts,
                d=[round(dist(t), 3) for t in ts],
                t5m=round(sprint.time_to(5.0, kmh, a0, reaction_s), 3),
                d1s=round(dist(1.0), 3),
                d2s=round(dist(2.0), 3),
            )
        )
    ref = curves[0] if curves else None
    gap1s = {c.player_id: round(c.d1s - ref.d1s, 2) for c in curves} if ref else {}
    gap2s = {c.player_id: round(c.d2s - ref.d2s, 2) for c in curves} if ref else {}
    return RaceResult(curves=curves, gap1s=gap1s, gap2s=gap2s, reaction_s=reaction_s, label=LABEL)

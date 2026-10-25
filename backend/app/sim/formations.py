"""Formation slots in the team's attacking frame (x: own goal 0 -> opponent goal 100,
y: right touchline 0 -> left 100). Used for lineup selection, matchups and the UI's
visual-only player dots."""

from dataclasses import dataclass

from app.models import Position


@dataclass(frozen=True)
class Slot:
    slot: str
    position: Position
    x: float
    y: float


FORMATIONS: dict[str, list[Slot]] = {
    "4-3-3": [
        Slot("GK", "GK", 6, 50),
        Slot("RB", "RB", 28, 10),
        Slot("RCB", "CB", 22, 36),
        Slot("LCB", "CB", 22, 64),
        Slot("LB", "LB", 28, 90),
        Slot("CDM", "CDM", 40, 50),
        Slot("RCM", "CM", 52, 30),
        Slot("LCM", "CM", 52, 70),
        Slot("RW", "RW", 74, 12),
        Slot("ST", "ST", 80, 50),
        Slot("LW", "LW", 74, 88),
    ],
    "4-2-3-1": [
        Slot("GK", "GK", 6, 50),
        Slot("RB", "RB", 28, 10),
        Slot("RCB", "CB", 22, 36),
        Slot("LCB", "CB", 22, 64),
        Slot("LB", "LB", 28, 90),
        Slot("RDM", "CDM", 40, 38),
        Slot("LDM", "CDM", 40, 62),
        Slot("RW", "RW", 68, 14),
        Slot("CAM", "CAM", 64, 50),
        Slot("LW", "LW", 68, 86),
        Slot("ST", "ST", 80, 50),
    ],
}


def formation_slots(formation: str) -> tuple[str, list[Slot]]:
    """Return a supported formation (falls back to 4-3-3) and its slots."""
    name = formation if formation in FORMATIONS else "4-3-3"
    return name, FORMATIONS[name]

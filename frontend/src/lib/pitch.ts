// Pitch geometry. Event coordinates are 0-100 in the actor's attacking frame
// (docs/schema.md §6). The UI shows home attacking left -> right on a 105 x 68
// SVG. Player dots are visual-only (formation slot + ball drift), never data.

import type { MatchEvent } from "./types";

export const PITCH_W = 105;
export const PITCH_H = 68;

// Mirrors backend/app/sim/formations.py
const SLOTS: Record<string, [number, number]> = {
  GK: [6, 50], RB: [28, 10], RCB: [22, 36], LCB: [22, 64], LB: [28, 90],
  CDM: [40, 50], RCM: [52, 30], LCM: [52, 70], RDM: [40, 38], LDM: [40, 62],
  CAM: [64, 50], ST: [80, 50],
};
const WIDE: Record<string, Record<string, [number, number]>> = {
  "4-3-3": { RW: [74, 12], LW: [74, 88] },
  "4-2-3-1": { RW: [68, 14], LW: [68, 86] },
};

export function slotPosition(slot: string, formation: string): [number, number] {
  return WIDE[formation]?.[slot] ?? SLOTS[slot] ?? [50, 50];
}

/** Team frame (0-100) -> SVG coordinates. */
export function toSvg(x: number, y: number, isHome: boolean): [number, number] {
  const ax = isHome ? x : 100 - x;
  const ay = isHome ? 100 - y : y;
  return [(ax / 100) * PITCH_W, (ay / 100) * PITCH_H];
}

/** Where the ball is after an event, in SVG coordinates. */
export function ballAfter(ev: MatchEvent, isHome: boolean): [number, number] | null {
  const moved = (ev.event_type === "pass" || ev.event_type === "carry" || ev.event_type === "take_on")
    && ev.outcome === "success" && ev.end_x != null && ev.end_y != null;
  if (moved) return toSvg(ev.end_x!, ev.end_y!, isHome);
  if (ev.start_x != null && ev.start_y != null) return toSvg(ev.start_x, ev.start_y, isHome);
  return null;
}

/**
 * Visual dot position: formation slot, drifting with the ball along the pitch
 * (block shifts up/down) and slightly towards its flank.
 */
export function dotPosition(
  slot: string,
  formation: string,
  isHome: boolean,
  ballSvg: [number, number] | null,
): [number, number] {
  const [sx, sy] = slotPosition(slot, formation);
  if (!ballSvg || slot === "GK") return toSvg(sx, sy, isHome);
  // ball in this team's frame
  const bxAbs = (ballSvg[0] / PITCH_W) * 100;
  const byAbs = (ballSvg[1] / PITCH_H) * 100;
  const bx = isHome ? bxAbs : 100 - bxAbs;
  const by = isHome ? 100 - byAbs : byAbs;
  const x = Math.min(96, Math.max(4, sx + (bx - 50) * 0.38));
  const y = Math.min(97, Math.max(3, sy + (by - 50) * 0.18));
  return toSvg(x, y, isHome);
}

export function clockLabel(sec: number): string {
  const s = Math.max(0, Math.floor(sec));
  if (s > 5400) return `90+${Math.ceil((s - 5400) / 60)}'`;
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

export const minuteOf = (sec: number) => Math.min(90, Math.floor(sec / 60) + 1);

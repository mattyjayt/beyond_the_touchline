// Display helpers for the assistant-coach page. Labels only - no football arithmetic.

import type { Move, RadarAxis, Recommendation } from "./types";

/** Stable identity of an option across refetches (rec_id embeds asof and rank). */
export function optionKey(o: Recommendation): string {
  if (o.option_type === "keep") return "keep";
  const legs = o.moves.map((m) => `${m.player_id}:${m.from_slot ?? "-"}>${m.to_slot ?? "-"}`).sort();
  return `${o.option_type}|${legs.join(",")}`;
}

export const TYPE_CHIP: Record<Recommendation["option_type"], string> = {
  keep: "KEEP",
  substitution: "SUB",
  position_swap: "SWAP",
  sub_and_swap: "SUB + SWAP",
};

export function moveText(m: Move, name: (id: string) => string): string {
  const who = name(m.player_id);
  if (m.kind === "on") return `${who} on → ${m.to_slot}`;
  if (m.kind === "off") return `${who} off (${m.from_slot})`;
  return `${who} ${m.from_slot} → ${m.to_slot}`;
}

/** The player who ends up in the hot slot for an option (null for KEEP). */
export function incoming(o: Recommendation | null | undefined): string | null {
  return o && o.option_type !== "keep" ? o.incoming_player_id : null;
}

export const DIM_LABELS: Record<string, string> = {
  L: "Live form",
  F: "Fit",
  M: "Duel win",
  A: "Attack",
  G: "Game state",
  R: "Risk",
};

export const AXIS_LABELS: Record<RadarAxis, string> = {
  pace: "Pace",
  acceleration: "Acceleration",
  agility: "Agility",
  stamina: "Stamina",
  defending: "Defending",
  stance: "Stance",
  duel_win: "1v1 win %",
};

/** Radar axis -> the study variables that measure it (links the radar and importance panels). */
export const AXIS_VARS: Record<RadarAxis, string[]> = {
  pace: ["phy.def_top_speed_kmh", "phy.att_top_speed_kmh", "phy.speed_kmh_diff"],
  acceleration: ["duel.burst", "phy.accel_idx_diff", "phy.def_accel_ms2", "phy.att_accel_ms2",
    "phy.def_time_0_5m_s", "phy.att_time_0_5m_s"],
  agility: ["duel.agil", "phy.agility_idx_diff", "phy.def_agility_idx", "phy.att_agility_idx"],
  stamina: ["phy.def_stamina_idx", "phy.att_stamina_idx", "ctx.def_fatigue_mult",
    "ctx.att_fatigue_mult", "ctx.def_minutes_on", "ctx.att_minutes_on"],
  defending: ["pri.def_defending", "duel.tech", "pri.tech_gap"],
  stance: ["phy.def_stance_idx", "ctx.stance_draw", "duel.ctx"],
  duel_win: [],
};

export function axisOfVar(varId: string): RadarAxis | null {
  const hit = (Object.keys(AXIS_VARS) as RadarAxis[]).find((a) => AXIS_VARS[a].includes(varId));
  return hit ?? null;
}

export const FAMILY_COLOR: Record<string, string> = {
  PHY: "#c6f432",
  PRI: "#b48cff",
  CTX: "#ffb020",
  DUEL: "#6cabdd",
  HIS: "#7d8a85",
  EVT: "#ff8a5c",
  RAT: "#3ddc84",
};

export const pct = (v: number | null | undefined, digits = 0) =>
  v == null ? "n/a" : `${(v * 100).toFixed(digits)}%`;

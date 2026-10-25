import type { MatchEvent, Player } from "./types";

export type Players = Record<string, Player>;

export const shortName = (players: Players, id: string | null | undefined) => {
  if (!id) return "—";
  const name = players[id]?.display_name ?? id;
  const parts = name.split(" ");
  return parts.length > 1 ? parts.slice(1).join(" ") : name;
};

/** Events worth showing in the condensed feed. */
export function isNotable(ev: MatchEvent): boolean {
  switch (ev.event_type) {
    case "shot": case "card": case "substitution": case "period_start": case "period_end":
    case "take_on": case "foul":
      return true;
    case "restart":
      return ev.qualifiers.restart_type === "corner";
    case "pass":
      return Boolean(ev.qualifiers.through_ball) && ev.outcome === "success";
    default:
      return false;
  }
}

export function describe(ev: MatchEvent, players: Players): string {
  const who = shortName(players, ev.player_id);
  const opp = shortName(players, ev.opponent_id);
  const to = shortName(players, ev.recipient_id);
  const xg = typeof ev.qualifiers.xg === "number" ? ` · xG ${ev.qualifiers.xg.toFixed(2)}` : "";
  switch (ev.event_type) {
    case "period_start": return ev.period === 1 ? "Kick-off" : "Second half under way";
    case "period_end": return ev.period === 1 ? "Half-time" : "Full-time";
    case "restart": {
      const kind = String(ev.qualifiers.restart_type ?? "restart").replace("_", " ");
      return `${kind[0].toUpperCase()}${kind.slice(1)} — ${who}`;
    }
    case "pass":
      if (ev.outcome === "success") return `${who} → ${to}${ev.qualifiers.through_ball ? " (through ball)" : ""}`;
      return `${who}'s pass to ${to} goes astray`;
    case "carry": return ev.outcome === "success" ? `${who} drives forward` : `${who} loses the ball`;
    case "take_on": return ev.outcome === "success" ? `${who} beats ${opp}` : `${who} stopped by ${opp}`;
    case "shot":
      switch (ev.outcome) {
        case "goal": return `GOAL — ${who}${xg}`;
        case "saved": return `${who} forces a save${xg}`;
        case "blocked": return `${who}'s shot is blocked${xg}`;
        default: return `${who} shoots wide${xg}`;
      }
    case "tackle": return `${who} wins it from ${opp}`;
    case "interception": return `${who} intercepts`;
    case "foul": return `Foul by ${who} on ${opp}`;
    case "card": {
      const c = String(ev.qualifiers.card ?? "yellow");
      return `${c === "yellow" ? "Yellow" : c === "red" ? "Red" : "Second yellow"} card — ${who}`;
    }
    case "substitution": return `${to} on for ${who}`;
  }
}

export function eventIcon(ev: MatchEvent): string {
  if (ev.event_type === "shot" && ev.outcome === "goal") return "⚽";
  if (ev.event_type === "card") return ev.qualifiers.card === "yellow" ? "🟨" : "🟥";
  if (ev.event_type === "substitution") return "⇄";
  if (ev.event_type === "shot") return "◎";
  if (ev.event_type === "take_on") return ev.outcome === "success" ? "↗" : "✕";
  if (ev.event_type.startsWith("period")) return "⏱";
  return "·";
}

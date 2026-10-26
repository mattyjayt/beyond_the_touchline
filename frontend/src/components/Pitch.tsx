"use client";

import { AnimatePresence, motion } from "motion/react";
import { PitchMarkings } from "@/components/PitchMarkings";
import { ballAfter, dotPosition, PITCH_H, PITCH_W, toSvg } from "@/lib/pitch";
import type { MatchDetail, MatchEvent, MatchState } from "@/lib/types";

interface Props {
  detail: MatchDetail;
  state: MatchState | null;
  events: MatchEvent[];
  highlighted: MatchEvent[];
}

const spring = { type: "spring", stiffness: 60, damping: 16, mass: 0.8 } as const;

export function Pitch({ detail, state, events, highlighted }: Props) {
  const { match, home, away, players } = detail;
  const isHome = (teamId: string) => teamId === match.home_team_id;

  const last = [...events].reverse().find((e) => e.start_x != null);
  const ball = last ? ballAfter(last, isHome(last.team_id)) : ([PITCH_W / 2, PITCH_H / 2] as [number, number]);
  const trail = last && last.start_x != null && last.end_x != null && last.event_type !== "shot"
    ? [toSvg(last.start_x, last.start_y!, isHome(last.team_id)), toSvg(last.end_x, last.end_y!, isHome(last.team_id))]
    : null;
  const actorId = last?.outcome === "success" && last.event_type === "pass" ? last.recipient_id : last?.player_id;

  const onPitch = state?.on_pitch ?? detail.roster
    .filter((r) => r.roster_status === "starter")
    .map((r) => ({ player_id: r.player_id, team_id: r.team_id, formation_slot: r.formation_slot!, live_rating: null }));

  return (
    <svg viewBox={`-3 -3 ${PITCH_W + 6} ${PITCH_H + 6}`} className="w-full h-auto select-none" role="img"
      aria-label="Simulated pitch view">
      <PitchMarkings />

      {trail && (
        <motion.line key={last!.event_id} x1={trail[0][0]} y1={trail[0][1]} x2={trail[1][0]} y2={trail[1][1]}
          stroke="var(--pitch-line)" strokeWidth="0.35" strokeDasharray="1 0.8"
          initial={{ pathLength: 0, opacity: 0.9 }} animate={{ pathLength: 1, opacity: 0.5 }} transition={{ duration: 0.4 }} />
      )}

      <AnimatePresence>
        {highlighted.map((ev) => {
          if (ev.start_x == null) return null;
          const [hx, hy] = toSvg(ev.start_x, ev.start_y!, isHome(ev.team_id));
          return (
            <motion.circle key={`hl-${ev.event_id}`} cx={hx} cy={hy} r="2.6" fill="none" stroke="var(--accent)"
              strokeWidth="0.5" initial={{ scale: 0.4, opacity: 0 }} animate={{ scale: [1, 1.5, 1], opacity: 1 }}
              exit={{ opacity: 0 }} transition={{ scale: { repeat: Infinity, duration: 1.6 } }}
              style={{ transformBox: "fill-box", transformOrigin: "center" }} />
          );
        })}
      </AnimatePresence>

      {onPitch.map((p) => {
        const team = isHome(p.team_id) ? home : away;
        const formation = isHome(p.team_id) ? match.home_formation : match.away_formation;
        const isActor = p.player_id === actorId;
        const [x, y] = isActor && ball ? ball : dotPosition(p.formation_slot, formation, isHome(p.team_id), ball);
        const player = players[p.player_id];
        const kit = isHome(p.team_id) ? team.primary_color : team.secondary_color;
        const ink = isHome(p.team_id) ? team.secondary_color : team.primary_color;
        return (
          <motion.g key={p.player_id} initial={false} animate={{ x, y }} transition={spring}>
            <title>{`${player?.display_name ?? p.player_id} (${p.formation_slot})`}</title>
            {isActor && <circle r="2.7" fill="none" stroke="var(--accent)" strokeWidth="0.35" />}
            <circle r="1.9" fill={kit} stroke={ink} strokeWidth="0.35" />
            <text y="0.62" textAnchor="middle" fontSize="1.7" fontWeight="700" fill={ink}
              style={{ fontFamily: "var(--font-geist-mono)" }}>
              {player?.shirt_number ?? ""}
            </text>
          </motion.g>
        );
      })}

      {ball && (
        <motion.circle r="0.85" fill="#fff" stroke="#111" strokeWidth="0.2" initial={false}
          animate={{ cx: ball[0], cy: ball[1] }} transition={{ type: "spring", stiffness: 120, damping: 18 }} />
      )}
    </svg>
  );
}

"use client";

import { motion } from "motion/react";
import { PALETTE, linePath, polar } from "@/lib/chart";
import { AXIS_LABELS } from "@/lib/bench";
import { RADAR_AXES, type PlayerCard, type RadarAxis } from "@/lib/types";

const S = 340;
const C = S / 2;
const R = 112;
const angle = (i: number) => (i * 2 * Math.PI) / RADAR_AXES.length;

function shape(card: PlayerCard): string {
  return `${linePath(RADAR_AXES.map((a, i) => polar(C, C, (R * card.profile[a]) / 100, angle(i))))} Z`;
}

/** Fixed 0-100 axes: the tormentor vs the selected candidate, with the current defender as a ghost. */
export function RadarCompare({ tormentor, candidate, current, highlightVar, onHighlightVar }: {
  tormentor: PlayerCard | null;
  candidate: PlayerCard | null;
  current: PlayerCard | null;
  highlightVar: RadarAxis | null;
  onHighlightVar: (axis: RadarAxis | null) => void;
}) {
  return (
    <section className="col-span-12 flex flex-col gap-2 rounded-2xl border border-[var(--line)] bg-[var(--panel)] p-3 md:col-span-6">
      <div className="flex flex-wrap items-baseline gap-2">
        <h2 className="text-sm font-semibold">Profile vs the tormentor</h2>
        <span className="text-xs text-[var(--muted)]">0–100 · synthetic profiles · hover an axis</span>
      </div>
      {!tormentor ? (
        <p className="py-10 text-center text-xs text-[var(--muted)]">Appears once a duel is being lost.</p>
      ) : (
        <>
          <svg viewBox={`0 0 ${S} ${S}`} className="mx-auto h-auto w-full max-w-[380px]" role="img" aria-label="Radar comparison">
            {[25, 50, 75, 100].map((v) => (
              <path key={v} d={`${linePath(RADAR_AXES.map((_, i) => polar(C, C, (R * v) / 100, angle(i))))} Z`}
                fill="none" stroke={PALETTE.grid} />
            ))}
            {RADAR_AXES.map((a, i) => {
              const [x, y] = polar(C, C, R, angle(i));
              const [lx, ly] = polar(C, C, R + 22, angle(i));
              const lit = highlightVar === a;
              return (
                <g key={a} onMouseEnter={() => onHighlightVar(a)} onMouseLeave={() => onHighlightVar(null)} className="cursor-default">
                  <title>{[tormentor, candidate, current].filter((c): c is PlayerCard => !!c)
                    .map((c) => `${c.name}: ${realUnits(c, a)}`).join("\n")}</title>
                  <line x1={C} y1={C} x2={x} y2={y} stroke={lit ? "var(--accent)" : PALETTE.grid} strokeWidth={lit ? 1.5 : 1} />
                  <text x={lx} y={ly + 3} textAnchor="middle" fontSize="10.5" fontWeight={lit ? 700 : 400}
                    fill={lit ? "var(--accent)" : "var(--fg-soft)"}>{AXIS_LABELS[a]}</text>
                  <circle cx={lx} cy={ly} r="16" fill="transparent" />
                </g>
              );
            })}
            {current && current.player_id !== candidate?.player_id && (
              <path d={shape(current)} fill="none" stroke={PALETTE.ghost} strokeDasharray="4 3" strokeWidth="1.5" />
            )}
            <motion.path initial={false} animate={{ d: shape(tormentor) }} fill="color-mix(in srgb, var(--them) 18%, transparent)"
              stroke={PALETTE.them} strokeWidth="2" />
            {candidate && (
              <motion.path initial={false} animate={{ d: shape(candidate) }} transition={{ type: "spring", stiffness: 90, damping: 16 }}
                fill="color-mix(in srgb, var(--us) 30%, transparent)" stroke={PALETTE.us} strokeWidth="2.2" />
            )}
          </svg>
          <div className="flex flex-wrap justify-center gap-3 text-[11px]">
            <Legend colour={PALETTE.them} label={tormentor.name} />
            {candidate && <Legend colour={PALETTE.us} label={`${candidate.name} (candidate)`} />}
            {current && current.player_id !== candidate?.player_id && <Legend colour={PALETTE.ghost} label={`${current.name} (now)`} dashed />}
          </div>
          <p className="text-[11px] text-[var(--muted)]">1v1 win % = duel-model projection vs the tormentor (for the tormentor: his projected win % vs the current defender). Simulated.</p>
        </>
      )}
    </section>
  );
}

/** The physical quantity behind a 0-100 radar axis, in real units where one exists. */
function realUnits(c: PlayerCard, axis: RadarAxis): string {
  const v = c.profile[axis].toFixed(0);
  if (axis === "pace") return `${c.physical.top_speed_kmh.toFixed(1)} km/h (index ${v})`;
  if (axis === "acceleration") return `${c.physical.accel_ms2.toFixed(2)} m/s² (index ${v})`;
  if (axis === "duel_win") return `${v}% projected`;
  return `index ${v}`;
}

function Legend({ colour, label, dashed }: { colour: string; label: string; dashed?: boolean }) {
  return (
    <span className="inline-flex items-center gap-1.5 text-[var(--fg-soft)]">
      <span className="inline-block h-0 w-4 border-t-2" style={{ borderColor: colour, borderStyle: dashed ? "dashed" : "solid" }} />
      {label}
    </span>
  );
}

"use client";

import { AnimatePresence, motion } from "motion/react";
import { PitchMarkings } from "@/components/PitchMarkings";
import { PITCH_H, PITCH_W, slotPosition, toSvg } from "@/lib/pitch";
import type { Player, Recommendation } from "@/lib/types";

const spring = { type: "spring", stiffness: 70, damping: 15 } as const;

/** Our shape now, and after the selected option. Visual only: nothing is derived from dots. */
export function FormationPreview({ formation, slots, option, players, kit, ink }: {
  formation: string;
  slots: Record<string, string>;
  option: Recommendation | null;
  players: Record<string, Player>;
  kit: string;
  ink: string;
}) {
  const after: Record<string, string> = { ...slots };
  const movers = new Set<string>();
  for (const m of option?.moves ?? []) {
    movers.add(m.player_id);
    if (m.kind === "off") delete after[m.player_id];
    else if (m.to_slot) after[m.player_id] = m.to_slot;
  }
  return (
    <section className="col-span-12 flex flex-col gap-2 rounded-2xl border border-[var(--line)] bg-[var(--panel)] p-3 md:col-span-6">
      <div className="flex flex-wrap items-baseline gap-2">
        <h2 className="text-sm font-semibold">Shape after the change</h2>
        <span className="text-xs text-[var(--muted)]">{formation} · select an option card</span>
      </div>
      <svg viewBox={`-3 -3 ${PITCH_W + 6} ${PITCH_H + 6}`} className="mx-auto h-auto w-full max-w-[520px]" role="img"
        aria-label="Formation preview (visual only)">
        <PitchMarkings />
        <AnimatePresence>
          {Object.entries(after).map(([pid, slot]) => {
            const [x, y] = toSvg(...slotPosition(slot, formation), true);
            const glow = movers.has(pid) && option?.out_of_position;
            return (
              <motion.g key={pid} initial={{ opacity: 0, x, y }} animate={{ opacity: 1, x, y }} exit={{ opacity: 0 }} transition={spring}>
                <title>{`${players[pid]?.display_name ?? pid} (${slot})`}</title>
                {movers.has(pid) && <circle r="3.2" fill="none" stroke={glow ? "var(--warn)" : "var(--accent)"} strokeWidth="0.5" />}
                <circle r="2.2" fill={kit} stroke={ink} strokeWidth="0.35" />
                <text y="0.7" textAnchor="middle" fontSize="2" fontWeight="700" fill={ink} style={{ fontFamily: "var(--font-geist-mono)" }}>
                  {players[pid]?.shirt_number ?? ""}
                </text>
              </motion.g>
            );
          })}
        </AnimatePresence>
      </svg>
      <p className="text-center text-[11px] text-[var(--muted)]">Visual only, not data. Ringed: players the option moves{option?.out_of_position ? " (amber: out of position)" : ""}.</p>
    </section>
  );
}

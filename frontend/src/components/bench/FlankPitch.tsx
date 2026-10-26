"use client";

import { motion } from "motion/react";
import { useState } from "react";
import { PitchMarkings } from "@/components/PitchMarkings";
import { PITCH_H, PITCH_W, clockLabel, toSvg } from "@/lib/pitch";
import type { DuelLedger, DuelPoint } from "@/lib/types";

type Filter = "all" | "before" | "after";
const ZONES = 6; // heat columns along the flank (attacker-frame x 40..100)
const ZONE_FROM = 40;
const COLUMN_PX = 14; // column height per duel lost

const isLoss = (p: DuelPoint) => p.outcome === "lost" || p.outcome === "foul";

/**
 * Where the tormentor's 1v1s happened, on a CSS-3D tilted pitch. Points are in the attacker's
 * frame (the away side attacks right-to-left here), sized by the stored p_beat term. Labels
 * and the detail card live in a flat overlay, never in the tilted plane.
 */
export function FlankPitch({ ledger, swapSec, highlight, onHighlight, name }: {
  ledger: DuelLedger | null;
  swapSec: number | null;
  highlight: string[];
  onHighlight: (ids: string[]) => void;
  name: (id: string) => string;
}) {
  const [filter, setFilter] = useState<Filter>("all");
  const [picked, setPicked] = useState<DuelPoint | null>(null);
  const points = (ledger?.points ?? []).filter((p) =>
    filter === "all" || swapSec == null ? true : filter === "before" ? p.sec < swapSec : p.sec >= swapSec);

  const losses = new Array(ZONES).fill(0) as number[];
  for (const p of points.filter(isLoss)) {
    const z = Math.min(ZONES - 1, Math.max(0, Math.floor(((p.x - ZONE_FROM) / (100 - ZONE_FROM)) * ZONES)));
    losses[z] += 1;
  }
  const lit = new Set(highlight);

  return (
    <section className="col-span-12 flex flex-col gap-2 overflow-hidden rounded-2xl border border-[var(--line)] bg-[var(--panel)] p-3 lg:col-span-7">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-sm font-semibold">Where the duels happen</h2>
        <span className="text-xs text-[var(--muted)]">{ledger ? `${ledger.duels} duels · won ${ledger.won} · lost ${ledger.lost} · recovered ${ledger.recoveries} · fouls ${ledger.fouls}` : "no duels yet"}</span>
        <div className="ml-auto flex rounded-lg border border-[var(--line)] p-0.5 text-[11px]">
          {(["before", "after", "all"] as Filter[]).map((f) => (
            <button key={f} disabled={f !== "all" && swapSec == null} onClick={() => setFilter(f)}
              className={`rounded-md px-2 py-0.5 capitalize disabled:opacity-30 ${filter === f ? "bg-[var(--fg)] text-[var(--bg)]" : "text-[var(--muted)]"}`}>
              {f === "all" ? "All" : `${f} swap`}
            </button>
          ))}
        </div>
      </div>

      {/* the tilted plane is shorter than the flat one: pull the margins in so the panel hugs it */}
      <div className="relative -my-[7%] px-[4%]" style={{ perspective: "1100px" }}>
        <motion.div className="relative" style={{ transformStyle: "preserve-3d", transformOrigin: "50% 50%" }}
          initial={{ rotateX: 0 }} animate={{ rotateX: 45 }} transition={{ duration: 1.1, ease: "easeOut" }}>
          <svg viewBox={`-3 -3 ${PITCH_W + 6} ${PITCH_H + 6}`} className="block h-auto w-full" role="img"
            aria-label="Simulated duel locations on the right flank">
            <PitchMarkings />
            {points.map((p) => {
              const [x, y] = toSvg(p.x, p.y, false);
              const pBeat = typeof p.terms.p_beat === "number" ? p.terms.p_beat : 0.5;
              const colour = isLoss(p) ? "var(--loss)" : "var(--win)";
              return (
                <g key={p.event_id} onClick={() => { setPicked(p); onHighlight([p.event_id]); }} className="cursor-pointer">
                  {lit.has(p.event_id) && <circle cx={x} cy={y} r={3.2} fill="none" stroke="var(--accent)" strokeWidth="0.45" />}
                  <circle cx={x} cy={y} r={0.8 + 1.6 * pBeat} fill={colour} fillOpacity={0.8} stroke="#0008" strokeWidth="0.2">
                    <title>{`${clockLabel(p.sec)} · ${p.outcome} · p_beat ${pBeat}`}</title>
                  </circle>
                </g>
              );
            })}
          </svg>
          {losses.map((n, z) => {
            if (!n) return null;
            const ax = ZONE_FROM + ((z + 0.5) * (100 - ZONE_FROM)) / ZONES;
            const [sx, sy] = toSvg(ax, 92, false);
            return (
              <motion.div key={z} title={`${n} lost in this zone`}
                className="pointer-events-none absolute w-[4%] rounded-t-sm"
                style={{
                  left: `${((sx + 3) / (PITCH_W + 6)) * 100}%`, top: `${((sy + 3) / (PITCH_H + 6)) * 100}%`,
                  transformOrigin: "bottom", x: "-50%", y: "-100%", rotateX: -90,
                  background: "linear-gradient(to top, var(--loss), color-mix(in srgb, var(--loss) 30%, transparent))",
                }}
                initial={{ height: 0 }} animate={{ height: n * COLUMN_PX }} transition={{ delay: 0.9, duration: 0.6 }} />
            );
          })}
        </motion.div>
      </div>

      <div className="relative z-10 mt-2 flex flex-wrap items-start gap-3 text-[11px] text-[var(--muted)]">
        <span><span className="text-[var(--win)]">●</span> defender won / recovered</span>
        <span><span className="text-[var(--loss)]">●</span> beaten / fouled</span>
        <span>size = model p_beat · columns = losses per zone</span>
        {picked && (
          <div className="w-full rounded-lg border border-[var(--line)] bg-[var(--bg)] p-2 font-mono text-[11px] text-[var(--fg-soft)]">
            {picked.event_id} · {clockLabel(picked.sec)} · {name(picked.attacker_id)} vs {name(picked.defender_id)} · {picked.outcome}
            <div className="mt-1 text-[var(--muted)]">
              {["tech", "burst", "stance", "ctx", "script", "p_beat"].map((k) => `${k} ${picked.terms[k] ?? "–"}`).join(" · ")}
              {" "}(simulator model, uncalibrated)
            </div>
          </div>
        )}
      </div>
    </section>
  );
}

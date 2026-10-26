"use client";

import { animate } from "motion/react";
import { useEffect, useRef, useState } from "react";
import { PALETTE, linear, sampleAt } from "@/lib/chart";
import type { RaceResult } from "@/lib/types";

const HORIZON = 3;

/** 0-3 s acceleration race from the backend's sampled curves (the UI only interpolates). */
export function SprintRace({ race, ids, colours }: {
  race: RaceResult | null;
  ids: string[]; // curves to show, tormentor first
  colours: Record<string, string>;
}) {
  const [t, setT] = useState(HORIZON);
  const anim = useRef<ReturnType<typeof animate> | null>(null);
  useEffect(() => () => anim.current?.stop(), []);

  const play = () => {
    anim.current?.stop();
    anim.current = animate(0, HORIZON, { duration: HORIZON * 1.5, ease: "linear", onUpdate: setT });
  };

  const curves = (race?.curves ?? []).filter((c) => ids.includes(c.player_id))
    .sort((a, b) => ids.indexOf(a.player_id) - ids.indexOf(b.player_id));
  const maxD = Math.max(1, ...curves.map((c) => c.d[c.d.length - 1]));
  const x = linear([0, maxD], [0, 100]);
  const ref = race?.curves[0]?.player_id;

  return (
    <section className="col-span-12 flex flex-col gap-3 rounded-2xl border border-[var(--line)] bg-[var(--panel)] p-3 md:col-span-6">
      <div className="flex flex-wrap items-center gap-2">
        <h2 className="text-sm font-semibold">First steps: 0–3 s sprint</h2>
        <button onClick={play} className="ml-auto h-7 rounded-lg bg-[var(--fg)] px-3 text-xs font-semibold text-[var(--bg)]">
          {t < HORIZON ? "Replay" : "▶ Play"}
        </button>
      </div>
      {!curves.length ? (
        <p className="py-10 text-center text-xs text-[var(--muted)]">Appears once a duel is being lost.</p>
      ) : (
        <>
          <div className="flex flex-col gap-3">
            {curves.map((c) => {
              const d = sampleAt(c.t, c.d, t);
              const colour = colours[c.player_id] ?? PALETTE.ghost;
              return (
                <div key={c.player_id} className="flex flex-col gap-1">
                  <div className="flex items-baseline gap-2 text-[11px]">
                    <span className="font-medium" style={{ color: colour }}>{c.name}</span>
                    <span className="font-mono text-[var(--muted)]">
                      5 m in {c.t5m.toFixed(2)} s · {c.d1s.toFixed(2)} m @1 s · {c.d2s.toFixed(2)} m @2 s
                      {ref && c.player_id !== ref && race && (
                        <> · gap {fmtGap(race.gap1s[c.player_id])} @1 s, {fmtGap(race.gap2s[c.player_id])} @2 s</>
                      )}
                    </span>
                  </div>
                  <div className="relative h-5 rounded-full bg-[var(--grid)]">
                    {[5, 10, 15].filter((m) => m < maxD).map((m) => (
                      <span key={m} className="absolute inset-y-0 w-px bg-[var(--line)]" style={{ left: `${x(m)}%` }} />
                    ))}
                    <span className="absolute inset-y-1 left-0 rounded-full opacity-40" style={{ width: `${x(d)}%`, background: colour }} />
                    <span className="absolute top-1/2 h-3.5 w-3.5 -translate-x-1/2 -translate-y-1/2 rounded-full border-2 border-[var(--bg)]"
                      style={{ left: `${x(d)}%`, background: colour }} />
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex items-center gap-3">
            <input type="range" min={0} max={HORIZON} step={0.05} value={t} aria-label="Race time"
              onChange={(e) => { anim.current?.stop(); setT(Number(e.target.value)); }} className="w-full accent-[var(--us)]" />
            <span className="w-14 text-right font-mono text-xs tabular-nums">{t.toFixed(2)} s</span>
          </div>
          <p className="text-[11px] text-[var(--muted)]">
            {race?.label} Reaction {race?.reaction_s} s; gaps in metres vs {curves[0]?.name}. Ticks every 5 m.
          </p>
        </>
      )}
    </section>
  );
}

const fmtGap = (v: number | undefined) => (v == null ? "–" : `${v >= 0 ? "+" : ""}${v.toFixed(2)} m`);

"use client";

import { motion } from "motion/react";
import type { MatchDetail, MatchState, TeamLiveStats } from "@/lib/types";

const ROWS: { key: keyof TeamLiveStats; label: string; fmt?: (v: number) => string }[] = [
  { key: "possession_pct", label: "Possession", fmt: (v) => `${v.toFixed(0)}%` },
  { key: "shots", label: "Shots" },
  { key: "shots_on_target", label: "On target" },
  { key: "xg", label: "xG (illustrative)", fmt: (v) => v.toFixed(2) },
  { key: "passes", label: "Passes" },
  { key: "pass_accuracy", label: "Pass accuracy", fmt: (v) => `${v.toFixed(0)}%` },
];

export function StatsPanel({ detail, state }: { detail: MatchDetail; state: MatchState | null }) {
  const momentum = state?.momentum ?? 0;
  const m = Math.max(-1, Math.min(1, momentum / 15));
  return (
    <div className="rounded-2xl border border-[var(--line)] bg-[var(--panel)] p-4">
      <div className="mb-4">
        <div className="mb-1.5 flex justify-between text-xs text-[var(--muted)]">
          <span>{detail.home.code}</span><span>Momentum · last 5 min</span><span>{detail.away.code}</span>
        </div>
        <div className="relative h-2 overflow-hidden rounded-full bg-[var(--line)]">
          <div className="absolute inset-y-0 left-1/2 w-px bg-[var(--muted)]" />
          <motion.div className="absolute inset-y-0 rounded-full"
            animate={{ left: m >= 0 ? `${50 - m * 50}%` : "50%", width: `${Math.abs(m) * 50}%`,
              background: m >= 0 ? detail.home.primary_color : detail.away.primary_color }}
            transition={{ type: "spring", stiffness: 80, damping: 20 }} />
        </div>
      </div>
      <div className="space-y-2.5">
        {ROWS.map(({ key, label, fmt }) => {
          const h = Number(state?.home[key] ?? 0);
          const a = Number(state?.away[key] ?? 0);
          const total = h + a || 1;
          const f = fmt ?? ((v: number) => String(v));
          return (
            <div key={key}>
              <div className="mb-1 flex justify-between text-sm">
                <span className="font-mono tabular-nums">{f(h)}</span>
                <span className="text-xs text-[var(--muted)]">{label}</span>
                <span className="font-mono tabular-nums">{f(a)}</span>
              </div>
              <div className="flex h-1.5 gap-1">
                <div className="flex flex-1 justify-end overflow-hidden rounded-full bg-[var(--line)]">
                  <motion.div className="h-full rounded-full" style={{ background: detail.home.primary_color }}
                    animate={{ width: `${(h / total) * 100}%` }} />
                </div>
                <div className="flex-1 overflow-hidden rounded-full bg-[var(--line)]">
                  <motion.div className="h-full rounded-full" style={{ background: detail.away.primary_color }}
                    animate={{ width: `${(a / total) * 100}%` }} />
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

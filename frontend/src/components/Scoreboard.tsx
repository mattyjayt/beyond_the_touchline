"use client";

import { AnimatePresence, motion } from "motion/react";
import { clockLabel } from "@/lib/pitch";
import type { MatchDetail, MatchState } from "@/lib/types";

export function Scoreboard({ detail, state, clock }: { detail: MatchDetail; state: MatchState | null; clock: number }) {
  const { home, away, match } = detail;
  const status = state?.status ?? "scheduled";
  const period = clock >= 2700 ? "2H" : "1H";
  return (
    <div className="flex items-center justify-between gap-4 rounded-2xl border border-[var(--line)] bg-[var(--panel)] px-5 py-3">
      <TeamBlock name={home.name} code={home.code} color={home.primary_color} formation={match.home_formation} />
      <div className="flex flex-col items-center">
        <div className="flex items-center gap-3 font-mono text-4xl font-semibold tabular-nums">
          <Score value={state?.home.score ?? 0} />
          <span className="text-[var(--muted)]">–</span>
          <Score value={state?.away.score ?? 0} />
        </div>
        <div className="mt-1 flex items-center gap-2 text-xs text-[var(--muted)]">
          {status === "live" && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-[var(--live)]" />}
          <span className="font-mono tabular-nums">{status === "finished" ? "FT" : `${period} · ${clockLabel(clock)}`}</span>
        </div>
      </div>
      <TeamBlock name={away.name} code={away.code} color={away.primary_color} formation={match.away_formation} right />
    </div>
  );
}

function Score({ value }: { value: number }) {
  return (
    <span className="relative inline-block w-[1ch] overflow-hidden">
      <AnimatePresence mode="popLayout" initial={false}>
        <motion.span key={value} className="inline-block" initial={{ y: "-100%", opacity: 0 }}
          animate={{ y: 0, opacity: 1 }} exit={{ y: "100%", opacity: 0 }} transition={{ duration: 0.35 }}>
          {value}
        </motion.span>
      </AnimatePresence>
    </span>
  );
}

function TeamBlock({ name, code, color, formation, right }: {
  name: string; code: string; color: string; formation: string; right?: boolean;
}) {
  return (
    <div className={`flex min-w-0 flex-1 items-center gap-3 ${right ? "flex-row-reverse text-right" : ""}`}>
      <div className="grid h-10 w-10 shrink-0 place-items-center rounded-xl text-sm font-bold text-white"
        style={{ background: color }}>{code}</div>
      <div className="min-w-0">
        <div className="truncate font-semibold">{name}</div>
        <div className="text-xs text-[var(--muted)]">{formation}</div>
      </div>
    </div>
  );
}

"use client";

import Link from "next/link";
import { clockLabel } from "@/lib/pitch";
import { pct } from "@/lib/bench";
import type { BenchView, MatchDetail } from "@/lib/types";

const MATCH_END = 5400;

export function CoachHeader({ detail, view, asof, clock, onAsof }: {
  detail: MatchDetail;
  view: BenchView | null;
  asof: number | null;
  clock: number;
  onAsof: (sec: number | null) => void;
}) {
  const { home, away } = detail;
  const shown = view?.asof_sec ?? asof ?? clock;
  const alert = view?.alert;
  const name = (id: string) => detail.players[id]?.display_name ?? id;
  return (
    <header className="col-span-12 flex flex-col gap-3 rounded-2xl border border-[var(--line)] bg-[var(--panel)] p-4">
      <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
        <Link href="/" className="text-xs text-[var(--muted)] hover:text-[var(--fg)]">← Match centre</Link>
        <h1 className="text-base font-semibold tracking-tight">Assistant coach</h1>
        <span className="rounded-md border border-[var(--warn)] px-2 py-0.5 text-[10px] font-bold tracking-widest text-[var(--warn)]">SIMULATED</span>
        <div className="ml-auto flex items-center gap-3 font-mono tabular-nums">
          <span className="text-sm">{home.code}</span>
          <span className="text-2xl font-semibold">{view?.score[home.team_id] ?? 0}–{view?.score[away.team_id] ?? 0}</span>
          <span className="text-sm">{away.code}</span>
          <span className="text-xs text-[var(--muted)]">{clockLabel(shown)}</span>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {alert ? (
          <span className={`inline-flex items-center gap-2 rounded-full border px-3 py-1 text-xs ${view?.alert_active
            ? "border-[var(--loss)] bg-[color-mix(in_srgb,var(--loss)_14%,transparent)] text-[var(--fg)]"
            : "border-[var(--line)] text-[var(--muted)]"}`}>
            <span className={`h-2 w-2 rounded-full ${view?.alert_active ? "animate-pulse bg-[var(--loss)]" : "bg-[var(--muted)]"}`} />
            {name(alert.attacker_id).split(" ").slice(-1)[0]} vs {alert.defender_slot}: beaten {alert.beaten_20m} in 20&apos;
            <span className="text-[var(--muted)]">· win {pct(alert.win_pct_20m)} (n={alert.n_20m}) · since {Math.floor((alert.first_fired_sec ?? 0) / 60)}&apos;</span>
          </span>
        ) : (
          <span className="rounded-full border border-[var(--line)] px-3 py-1 text-xs text-[var(--muted)]">No hot duel yet</span>
        )}
        <span className="text-xs text-[var(--muted)]">{home.name} defending · everything here is simulated</span>
      </div>

      <div className="flex items-center gap-3">
        <input type="range" min={0} max={MATCH_END} step={30} value={Math.min(asof ?? clock, MATCH_END)}
          onChange={(e) => onAsof(Number(e.target.value))} aria-label="View the bench as of a match second"
          className="w-full accent-[var(--us)]" />
        <button onClick={() => onAsof(null)}
          className={`h-8 shrink-0 rounded-lg px-3 text-xs font-semibold ${asof === null
            ? "bg-[var(--live)] text-black" : "border border-[var(--line)] text-[var(--muted)] hover:text-[var(--fg)]"}`}>
          {asof === null ? "● Live" : "Go live"}
        </button>
      </div>
      {asof !== null && asof > clock && (
        <p className="text-[11px] text-[var(--muted)]">The replay is at {clockLabel(clock)}: the view stops there (no future events).</p>
      )}
    </header>
  );
}

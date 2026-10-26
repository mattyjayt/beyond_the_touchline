"use client";

import { motion } from "motion/react";
import { pct } from "@/lib/bench";
import type { DuelLedger, SwapImpact as Impact } from "@/lib/types";

interface Row {
  label: string;
  before: number | null;
  after: number | null;
  fmt: (v: number | null) => string;
  better: "higher" | "lower";
}

/** Before vs after the real position_change, from backend ledgers (20' before vs since). */
export function SwapImpact({ impact, executedRank, name }: {
  impact: Impact | null;
  executedRank: number | null;
  name: (id: string) => string;
}) {
  if (!impact) {
    return (
      <section className="col-span-12 grid place-items-center gap-1 rounded-2xl border border-dashed border-[var(--line)] bg-[var(--panel)] p-6 text-center md:col-span-6">
        <span className="text-2xl">🔒</span>
        <h2 className="text-sm font-semibold">Swap impact</h2>
        <p className="text-xs text-[var(--muted)]">Unlocks after the 70&apos; change (when the replay clock passes it).</p>
      </section>
    );
  }
  const { before: b, after: a } = impact;
  const rows: Row[] = [
    { label: "Defender win %", before: b.win_pct, after: a.win_pct, fmt: (v) => pct(v), better: "higher" },
    { label: "Duels lost / 10'", before: b.beaten_per_10, after: a.beaten_per_10, fmt: num(2), better: "lower" },
    { label: "Channel shots", before: b.channel_shots, after: a.channel_shots, fmt: num(0), better: "lower" },
    { label: "Channel xG", before: b.channel_xg, after: a.channel_xg, fmt: num(2), better: "lower" },
  ];
  const who = (l: DuelLedger) => l.defender_ids.map(name).join(", ") || "–";
  return (
    <section className="col-span-12 flex flex-col gap-3 rounded-2xl border border-[var(--line)] bg-[var(--panel)] p-3 md:col-span-6">
      <div className="flex flex-wrap items-baseline gap-2">
        <h2 className="text-sm font-semibold">Swap impact</h2>
        <span className="text-xs text-[var(--muted)]">{Math.floor(impact.swap_sec / 60)}&apos; change · 20&apos; before vs since</span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-[11px]">
        <Side colour="var(--ghost)" title="Before" who={who(b)} n={b.duels} />
        <Side colour="var(--us)" title="After" who={who(a)} n={a.duels} />
      </div>
      <div className="flex flex-col gap-2">
        {rows.map((r) => {
          const max = Math.max(1e-9, r.before ?? 0, r.after ?? 0);
          const improved = r.before != null && r.after != null &&
            (r.better === "higher" ? r.after > r.before : r.after < r.before);
          return (
            <div key={r.label} className="grid grid-cols-[110px_1fr] items-center gap-2 text-[11px]">
              <span className="text-[var(--muted)]">{r.label} {r.before != null && r.after != null && (
                <span className={improved ? "text-[var(--win)]" : "text-[var(--loss)]"}>{improved ? "▲" : "▼"}</span>)}</span>
              <div className="flex flex-col gap-0.5">
                {(["before", "after"] as const).map((k) => (
                  <div key={k} className="flex items-center gap-2">
                    <motion.span className="h-2 rounded-sm" initial={{ width: 0 }}
                      animate={{ width: `${((r[k] ?? 0) / max) * 70}%` }}
                      style={{ background: k === "before" ? "var(--ghost)" : "var(--us)" }} />
                    <span className="font-mono tabular-nums">{r.fmt(r[k])}</span>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
      <p className="text-[11px] text-[var(--fg-soft)]">
        {executedRank === 1
          ? "The swap Liverpool made was the advisor's #1 option at the alert."
          : executedRank != null
            ? `The swap Liverpool made was ranked #${executedRank} by the advisor at the alert, not #1. It is scripted at 70' whatever the advisor says.`
            : "The swap Liverpool made was not among the advisor's options at the alert. It is scripted at 70' whatever the advisor says."}
      </p>
      <p className="text-[11px] text-[var(--muted)]">Small samples (n above). Outcomes after the swap are unscripted model draws, not causal estimates. Simulated.</p>
    </section>
  );
}

const num = (digits: number) => (v: number | null) => (v == null ? "n/a" : v.toFixed(digits));

function Side({ colour, title, who, n }: { colour: string; title: string; who: string; n: number }) {
  return (
    <div className="rounded-lg border border-[var(--line)] px-2 py-1">
      <div className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-sm" style={{ background: colour }} />{title} · n={n}</div>
      <div className="truncate text-[var(--fg-soft)]">{who}</div>
    </div>
  );
}

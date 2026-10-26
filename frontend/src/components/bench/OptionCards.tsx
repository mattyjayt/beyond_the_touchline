"use client";

import { motion } from "motion/react";
import { DIM_LABELS, moveText, optionKey, pct, TYPE_CHIP } from "@/lib/bench";
import type { OptionDims, Recommendation } from "@/lib/types";

const CONF_STYLE: Record<string, string> = {
  low: "border-[var(--warn)] text-[var(--warn)]",
  medium: "border-[var(--them)] text-[var(--them)]",
  high: "border-[var(--live)] text-[var(--live)]",
};

export function OptionCards({ options, selected, chosen, onSelect, onChoose, name }: {
  options: Recommendation[];
  selected: string | null;
  chosen: string | null;
  onSelect: (key: string) => void;
  onChoose: (key: string | null) => void;
  name: (id: string) => string;
}) {
  return (
    <section className="col-span-12 flex flex-col gap-3">
      <div className="flex flex-wrap items-baseline gap-2">
        <h2 className="text-sm font-semibold">Options</h2>
        <span className="text-xs text-[var(--muted)]">Ranked by policy score vs KEEP · Policy weights · simulated · not causal</span>
      </div>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        {options.map((o) => {
          const key = optionKey(o);
          return (
            <OptionCard key={key} o={o} isSelected={selected === key} isChosen={chosen === key} name={name}
              onSelect={() => onSelect(key)} onChoose={() => onChoose(chosen === key ? null : key)} />
          );
        })}
      </div>
    </section>
  );
}

function OptionCard({ o, isSelected, isChosen, onSelect, onChoose, name }: {
  o: Recommendation;
  isSelected: boolean;
  isChosen: boolean;
  onSelect: () => void;
  onChoose: () => void;
  name: (id: string) => string;
}) {
  const isKeep = o.option_type === "keep";
  return (
    <motion.article layout onClick={onSelect}
      className={`flex cursor-pointer flex-col gap-3 rounded-2xl border bg-[var(--panel)] p-3 transition ${isSelected
        ? "border-[var(--us)] ring-1 ring-[var(--us)]" : "border-[var(--line)] hover:border-[var(--muted)]"}`}>
      <div className="flex items-center gap-2">
        <span className="font-mono text-xs text-[var(--muted)]">#{o.option_rank}</span>
        <span className={`rounded-md px-2 py-0.5 text-[10px] font-bold tracking-wider ${isKeep
          ? "bg-[var(--fg)] text-[var(--bg)]" : "bg-[var(--us)] text-white"}`}>{TYPE_CHIP[o.option_type]}</span>
        <span className={`rounded-md border px-1.5 py-0.5 text-[10px] ${CONF_STYLE[o.confidence]}`}>{o.confidence}</span>
        {o.out_of_position && (
          <span className="rounded-md border border-[var(--warn)] px-1.5 py-0.5 text-[10px] text-[var(--warn)]">Out of position</span>
        )}
        <span className="ml-auto font-mono text-xs tabular-nums text-[var(--muted)]">{(o.score ?? 0).toFixed(2)}</span>
      </div>

      <ul className="text-sm leading-snug">
        {isKeep ? <li>Keep the current shape</li> : o.moves.map((m) => <li key={m.player_id}>{moveText(m, name)}</li>)}
      </ul>

      {o.dims && <DimBars dims={o.dims} />}

      <div className="grid grid-cols-2 gap-2 text-[11px]">
        <Stat label="Projected 1v1 win" value={pct(o.projected_win_pct)} note="duel model" />
        <Stat label="Observed vs tormentor" value={pct(o.observed_win_pct)} note={`n=${o.n_observed}`} />
      </div>

      <ul className="flex flex-col gap-1 text-[11px] leading-snug">
        {o.pros.map((p) => <li key={p} className="text-[var(--fg-soft)]"><span className="text-[var(--win)]">+ </span>{p}</li>)}
        {o.cons.map((c) => <li key={c} className="text-[var(--fg-soft)]"><span className="text-[var(--loss)]">− </span>{c}</li>)}
      </ul>

      <button onClick={(e) => { e.stopPropagation(); onChoose(); }}
        className={`mt-auto h-8 rounded-lg text-xs font-semibold ${isChosen
          ? "bg-[var(--live)] text-black" : "border border-[var(--line)] text-[var(--muted)] hover:text-[var(--fg)]"}`}>
        {isChosen ? "✓ Chosen (logged locally)" : "Choose"}
      </button>
    </motion.article>
  );
}

function DimBars({ dims }: { dims: OptionDims }) {
  return (
    <div className="flex flex-col gap-1">
      {(Object.keys(DIM_LABELS) as (keyof OptionDims)[]).map((k) => {
        const v = dims[k];
        return (
          <div key={k} className="grid grid-cols-[64px_1fr_36px] items-center gap-2 text-[10px]" title={`${DIM_LABELS[k]} ${v.toFixed(2)} (−1…1)`}>
            <span className="text-[var(--muted)]">{DIM_LABELS[k]}</span>
            <div className="relative h-1.5 rounded-full bg-[var(--grid)]">
              <span className="absolute inset-y-0 left-1/2 w-px bg-[var(--muted)]" />
              <motion.span className="absolute inset-y-0 rounded-full" initial={false}
                animate={{ left: v >= 0 ? "50%" : `${50 + v * 50}%`, width: `${Math.abs(v) * 50}%` }}
                style={{ background: v >= 0 ? "var(--win)" : "var(--loss)" }} />
            </div>
            <span className="text-right font-mono tabular-nums">{v >= 0 ? "+" : ""}{v.toFixed(2)}</span>
          </div>
        );
      })}
    </div>
  );
}

function Stat({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <div className="rounded-lg border border-[var(--line)] px-2 py-1">
      <div className="text-[var(--muted)]">{label}</div>
      <div className="font-mono text-sm tabular-nums">{value} <span className="text-[10px] text-[var(--muted)]">{note}</span></div>
    </div>
  );
}

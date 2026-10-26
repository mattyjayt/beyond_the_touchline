"use client";

import { useState } from "react";
import { AXIS_VARS, FAMILY_COLOR, axisOfVar } from "@/lib/bench";
import type { ImportanceItem, RadarAxis } from "@/lib/types";

/** Top variables from the duel study (methodology demo: mirrors the generator). */
export function VariableImportance({ items, note, highlightVar, onHighlightVar }: {
  items: ImportanceItem[];
  note: string;
  highlightVar: RadarAxis | null;
  onHighlightVar: (axis: RadarAxis | null) => void;
}) {
  const [family, setFamily] = useState<string | null>(null);
  const families = [...new Set(items.map((i) => i.family))];
  const shown = items.filter((i) => !family || i.family === family);
  const max = Math.max(1e-9, ...items.map((i) => i.importance));
  const lit = new Set(highlightVar ? AXIS_VARS[highlightVar] : []);
  return (
    <section className="col-span-12 flex flex-col gap-3 rounded-2xl border border-[var(--line)] bg-[var(--panel)] p-3">
      <div className="flex flex-col gap-1">
        <h2 className="text-sm font-semibold">What drives a 1v1 here: variable importance</h2>
        <p className="text-[11px] text-[var(--warn)]">Methodology demo: importance mirrors the generator; not football truth.</p>
        {note && <p className="text-[11px] text-[var(--muted)]">{note}</p>}
      </div>
      {!items.length ? (
        <p className="text-xs text-[var(--muted)]">Run <code className="font-mono">uv run python -m app.analysis.duel_study</code> to populate.</p>
      ) : (
        <>
          <div className="flex flex-wrap gap-1.5">
            {[null, ...families].map((f) => (
              <button key={f ?? "all"} onClick={() => setFamily(f)}
                className={`rounded-full border px-2.5 py-0.5 text-[11px] ${family === f ? "border-[var(--fg)] text-[var(--fg)]" : "border-[var(--line)] text-[var(--muted)]"}`}>
                {f && <span className="mr-1 inline-block h-2 w-2 rounded-full" style={{ background: FAMILY_COLOR[f] }} />}
                {f ?? "All"}
              </button>
            ))}
          </div>
          <ol className="grid gap-x-6 gap-y-1 md:grid-cols-2">
            {shown.map((i) => (
              <li key={i.var_id} onMouseEnter={() => onHighlightVar(axisOfVar(i.var_id))} onMouseLeave={() => onHighlightVar(null)}
                className={`grid grid-cols-[22px_minmax(0,190px)_1fr] items-center gap-2 rounded px-1 text-[11px] ${lit.has(i.var_id) ? "bg-[var(--accent-soft)]" : ""}`}>
                <span className="font-mono text-[var(--muted)]">{i.rank}</span>
                <span className="truncate" title={`${i.var_id}: ${i.name}`}>{i.name}</span>
                <span className="flex items-center gap-2">
                  <span className="h-2 rounded-sm" style={{ width: `${(i.importance / max) * 80}%`, background: FAMILY_COLOR[i.family] ?? "var(--muted)" }} />
                  <span className="font-mono text-[10px] tabular-nums text-[var(--muted)]">{i.importance.toFixed(4)}</span>
                </span>
              </li>
            ))}
          </ol>
        </>
      )}
    </section>
  );
}

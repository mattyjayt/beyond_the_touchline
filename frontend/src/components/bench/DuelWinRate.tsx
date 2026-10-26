"use client";

import { useState } from "react";
import { PALETTE, linePath, linear, type Pt } from "@/lib/chart";
import { clockLabel } from "@/lib/pitch";
import { pct } from "@/lib/bench";
import type { DuelLedger, RollingPoint } from "@/lib/types";

const W = 600;
const H = 190;
const PAD = { l: 34, r: 12, t: 14, b: 22 };
const END = 5400;
const THRESHOLD = 0.3; // backend HOT_WIN_PCT (services/matchups.py)

/** Rolling 10-minute defender win rate against the tormentor, from the backend's series. */
export function DuelWinRate({ ledger, alertSec, swapSec, onSeek }: {
  ledger: DuelLedger | null;
  alertSec: number | null;
  swapSec: number | null;
  onSeek: (sec: number) => void;
}) {
  const [hover, setHover] = useState<RollingPoint | null>(null);
  const x = linear([0, END], [PAD.l, W - PAD.r]);
  const y = linear([0, 1], [H - PAD.b, PAD.t]);
  const rolling = ledger?.rolling ?? [];

  // split the line wherever the window is empty (win_pct null)
  const segments: Pt[][] = [];
  let cur: Pt[] = [];
  for (const r of rolling) {
    if (r.win_pct == null) {
      if (cur.length) segments.push(cur);
      cur = [];
    } else cur.push([x(r.sec), y(r.win_pct)]);
  }
  if (cur.length) segments.push(cur);

  const nearest = (clientX: number, el: SVGSVGElement) => {
    const box = el.getBoundingClientRect();
    const sec = ((clientX - box.left) / box.width * W - PAD.l) / (W - PAD.l - PAD.r) * END;
    return rolling.reduce<RollingPoint | null>(
      (best, r) => (!best || Math.abs(r.sec - sec) < Math.abs(best.sec - sec) ? r : best), null);
  };

  return (
    <section className="col-span-12 flex flex-col gap-2 rounded-2xl border border-[var(--line)] bg-[var(--panel)] p-3 lg:col-span-5">
      <div className="flex items-baseline gap-2">
        <h2 className="text-sm font-semibold">Duel win rate</h2>
        <span className="text-xs text-[var(--muted)]">defender, rolling 10&apos; · click to scrub</span>
      </div>
      <svg viewBox={`0 0 ${W} ${H}`} className="h-auto w-full cursor-crosshair select-none" role="img"
        aria-label="Rolling defender duel win rate"
        onMouseMove={(e) => setHover(nearest(e.clientX, e.currentTarget))} onMouseLeave={() => setHover(null)}
        onClick={(e) => { const n = nearest(e.clientX, e.currentTarget); if (n) onSeek(n.sec); }}>
        {[0, 0.25, 0.5, 0.75, 1].map((v) => (
          <g key={v}>
            <line x1={PAD.l} x2={W - PAD.r} y1={y(v)} y2={y(v)} stroke={PALETTE.grid} />
            <text x={PAD.l - 6} y={y(v) + 3} textAnchor="end" fontSize="9" fill="var(--muted)">{v * 100}%</text>
          </g>
        ))}
        {[0, 15, 30, 45, 60, 75, 90].map((m) => (
          <text key={m} x={x(m * 60)} y={H - 6} textAnchor="middle" fontSize="9" fill="var(--muted)">{m}&apos;</text>
        ))}
        <line x1={PAD.l} x2={W - PAD.r} y1={y(THRESHOLD)} y2={y(THRESHOLD)} stroke={PALETTE.loss} strokeDasharray="4 4" />
        <text x={W - PAD.r} y={y(THRESHOLD) - 4} textAnchor="end" fontSize="9" fill={PALETTE.loss}>alert ≤ 30%</text>
        {alertSec != null && <Marker x={x(alertSec)} label="alert" colour={PALETTE.loss} />}
        {swapSec != null && <Marker x={x(swapSec)} label="swap" colour={PALETTE.them} />}
        {segments.map((s, i) => (
          <path key={i} d={linePath(s)} fill="none" stroke={PALETTE.us} strokeWidth="2.2" strokeLinejoin="round" />
        ))}
        {hover && (
          <g pointerEvents="none">
            <line x1={x(hover.sec)} x2={x(hover.sec)} y1={PAD.t} y2={H - PAD.b} stroke="var(--fg-soft)" strokeDasharray="2 3" />
            {hover.win_pct != null && <circle cx={x(hover.sec)} cy={y(hover.win_pct)} r="3.5" fill={PALETTE.us} />}
            <text x={Math.min(x(hover.sec) + 6, W - 120)} y={PAD.t + 10} fontSize="10" fill="var(--fg)">
              {clockLabel(hover.sec)} · win {pct(hover.win_pct)} · n={hover.n}
            </text>
          </g>
        )}
      </svg>
      <p className="text-[11px] text-[var(--muted)]">Gaps = no duels in the window. Small n swings fast. Simulated.</p>
    </section>
  );
}

function Marker({ x, label, colour }: { x: number; label: string; colour: string }) {
  return (
    <g>
      <line x1={x} x2={x} y1={PAD.t} y2={H - PAD.b} stroke={colour} strokeWidth="1.2" />
      <text x={x + 3} y={PAD.t + 8} fontSize="9" fill={colour}>{label}</text>
    </g>
  );
}

// Tiny SVG chart helpers for the assistant-coach page. Pure geometry only: every number
// plotted comes from the backend (no win %, curves or scores are computed here).

export type Pt = [number, number];

/** Linear scale: domain -> range. */
export function linear([d0, d1]: [number, number], [r0, r1]: [number, number]) {
  const k = d1 === d0 ? 0 : (r1 - r0) / (d1 - d0);
  return (v: number) => r0 + (v - d0) * k;
}

/** Point at `angleRad` (0 = up, clockwise) on a circle of radius r around (cx, cy). */
export function polar(cx: number, cy: number, r: number, angleRad: number): Pt {
  return [cx + r * Math.sin(angleRad), cy - r * Math.cos(angleRad)];
}

export function linePath(points: Pt[]): string {
  return points.map(([x, y], i) => `${i ? "L" : "M"}${x.toFixed(2)} ${y.toFixed(2)}`).join(" ");
}

export function areaPath(points: Pt[], baseline: number): string {
  if (!points.length) return "";
  const first = points[0];
  const last = points[points.length - 1];
  return `${linePath(points)} L${last[0].toFixed(2)} ${baseline} L${first[0].toFixed(2)} ${baseline} Z`;
}

/** Colours come from CSS variables in globals.css so the theme stays in one place. */
export const PALETTE = {
  us: "var(--us)",
  them: "var(--them)",
  ghost: "var(--ghost)",
  grid: "var(--grid)",
  win: "var(--win)",
  loss: "var(--loss)",
} as const;

/** Linear interpolation of backend samples (t, d) at time `t` - display only. */
export function sampleAt(ts: number[], ds: number[], t: number): number {
  if (!ts.length) return 0;
  if (t <= ts[0]) return ds[0];
  for (let i = 1; i < ts.length; i++) {
    if (t <= ts[i]) {
      const f = (t - ts[i - 1]) / (ts[i] - ts[i - 1]);
      return ds[i - 1] + f * (ds[i] - ds[i - 1]);
    }
  }
  return ds[ds.length - 1];
}

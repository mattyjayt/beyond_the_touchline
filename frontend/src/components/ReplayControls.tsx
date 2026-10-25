"use client";

import { controlReplay } from "@/lib/api";
import { clockLabel } from "@/lib/pitch";
import type { MatchEvent, ReplayControl } from "@/lib/types";

const SPEEDS = [1, 10, 30, 60, 120];

export function ReplayControls({ matchId, control, clock, duration, keyEvents }: {
  matchId: string;
  control: ReplayControl | null;
  clock: number;
  duration: number;
  keyEvents: MatchEvent[];
}) {
  const playing = control?.status === "playing";
  const send = (action: Parameters<typeof controlReplay>[1], value?: number) =>
    controlReplay(matchId, action, value).catch(console.error);

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-[var(--line)] bg-[var(--panel)] px-4 py-3">
      <div className="flex flex-wrap items-center gap-2">
        <button onClick={() => send(playing ? "pause" : "play")}
          className="h-9 min-w-20 rounded-lg bg-[var(--accent)] px-4 text-sm font-semibold text-black transition hover:brightness-110">
          {playing ? "Pause" : control?.status === "finished" ? "Replay" : "Play"}
        </button>
        <button onClick={() => send("restart")}
          className="h-9 rounded-lg border border-[var(--line)] px-3 text-sm text-[var(--muted)] hover:text-[var(--fg)]">
          Restart
        </button>
        <div className="ml-auto flex items-center gap-1 rounded-lg border border-[var(--line)] p-1">
          {SPEEDS.map((s) => (
            <button key={s} onClick={() => send("speed", s)}
              className={`h-7 rounded-md px-2 font-mono text-xs ${control?.speed === s ? "bg-[var(--fg)] text-[var(--bg)]" : "text-[var(--muted)] hover:text-[var(--fg)]"}`}>
              {s}×
            </button>
          ))}
        </div>
      </div>
      <div className="relative">
        <input type="range" min={0} max={duration} step={30} value={Math.min(clock, duration)}
          onChange={(e) => send("seek", Number(e.target.value))}
          aria-label="Seek match time" className="w-full accent-[var(--accent)]" />
        <div className="pointer-events-none absolute inset-x-0 -top-1 h-2">
          {keyEvents.map((e) => (
            <span key={e.event_id} title={e.event_type}
              className={`absolute h-2 w-0.5 rounded ${e.event_type === "shot" ? "bg-[var(--accent)]" : "bg-[var(--muted)]"}`}
              style={{ left: `${(e.event_sec / duration) * 100}%` }} />
          ))}
        </div>
        <div className="mt-1 flex justify-between font-mono text-[10px] text-[var(--muted)]">
          <span>0:00</span><span>HT</span><span>{clockLabel(duration)}</span>
        </div>
      </div>
    </div>
  );
}

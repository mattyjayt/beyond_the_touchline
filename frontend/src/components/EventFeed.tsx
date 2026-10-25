"use client";

import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { describe, eventIcon, isNotable, type Players } from "@/lib/describe";
import { minuteOf } from "@/lib/pitch";
import type { MatchDetail, MatchEvent } from "@/lib/types";

export function EventFeed({ detail, events, highlightedIds, onSelect }: {
  detail: MatchDetail;
  events: MatchEvent[];
  highlightedIds: Set<string>;
  onSelect: (ids: string[]) => void;
}) {
  const [showAll, setShowAll] = useState(false);
  const players: Players = detail.players;
  const rows = (showAll ? events : events.filter((e) => isNotable(e) || highlightedIds.has(e.event_id)))
    .slice(-60)
    .reverse();

  return (
    <div className="flex min-h-0 flex-col rounded-2xl border border-[var(--line)] bg-[var(--panel)]">
      <div className="flex items-center justify-between border-b border-[var(--line)] px-4 py-2.5">
        <h2 className="text-sm font-semibold">Event stream</h2>
        <label className="flex items-center gap-2 text-xs text-[var(--muted)]">
          <input type="checkbox" checked={showAll} onChange={(e) => setShowAll(e.target.checked)} />
          all events
        </label>
      </div>
      <ol className="min-h-0 flex-1 overflow-y-auto px-2 py-1">
        <AnimatePresence initial={false}>
          {rows.map((ev) => {
            const team = ev.team_id === detail.home.team_id ? detail.home : detail.away;
            const goal = ev.event_type === "shot" && ev.outcome === "goal";
            const hl = highlightedIds.has(ev.event_id);
            return (
              <motion.li key={ev.event_id} layout initial={{ opacity: 0, y: -6 }} animate={{ opacity: 1, y: 0 }}
                onClick={() => onSelect([ev.event_id])}
                className={`flex cursor-pointer items-center gap-2.5 rounded-lg px-2 py-1.5 text-sm hover:bg-[var(--line)]
                  ${goal ? "font-semibold" : ""} ${hl ? "bg-[var(--accent-soft)] ring-1 ring-[var(--accent)]" : ""}`}>
                <span className="w-7 shrink-0 font-mono text-xs text-[var(--muted)] tabular-nums">{minuteOf(ev.event_sec)}&apos;</span>
                <span className="h-4 w-1 shrink-0 rounded" style={{ background: team.primary_color }} />
                <span className="w-4 shrink-0 text-center text-xs">{eventIcon(ev)}</span>
                <span className="min-w-0 flex-1 truncate">{describe(ev, players)}</span>
                <span className="shrink-0 font-mono text-[10px] text-[var(--muted)]">{ev.event_id.split("-").pop()}</span>
              </motion.li>
            );
          })}
        </AnimatePresence>
      </ol>
    </div>
  );
}

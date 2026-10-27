"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { AgentPanel } from "@/components/AgentPanel";
import { EventFeed } from "@/components/EventFeed";
import { Pitch } from "@/components/Pitch";
import { ReplayControls } from "@/components/ReplayControls";
import { Scoreboard } from "@/components/Scoreboard";
import { StatsPanel } from "@/components/StatsPanel";
import { matchClock, useMatchStream } from "@/hooks/useMatchStream";
import { API_BASE, APP_MODE, fetchDemoMatch, fetchHealth } from "@/lib/api";
import type { MatchDetail } from "@/lib/types";

export function MatchCenter() {
  const [detail, setDetail] = useState<MatchDetail | null>(null);
  const [provider, setProvider] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [highlightedIds, setHighlightedIds] = useState<string[]>([]);

  useEffect(() => {
    fetchDemoMatch().then(setDetail).catch((e) => setError(String(e)));
    fetchHealth().then((h) => setProvider(h.agent_provider)).catch(() => setProvider("offline"));
  }, []);

  const stream = useMatchStream(detail?.match.match_id ?? null);
  const clock = matchClock(stream);
  const highlightedSet = useMemo(() => new Set(highlightedIds), [highlightedIds]);
  const highlighted = useMemo(
    () => stream.events.filter((e) => highlightedSet.has(e.event_id)),
    [stream.events, highlightedSet],
  );
  const keyEvents = useMemo(
    () => stream.events.filter((e) => (e.event_type === "shot" && e.outcome === "goal") || e.event_type === "substitution" || e.event_type === "card"),
    [stream.events],
  );

  const hasAlert = stream.insights.some((i) => i.kind === "tactical_alert");

  if (error) {
    return (
      <div className="m-auto max-w-md p-8 text-center">
        <h1 className="text-lg font-semibold">Backend not reachable</h1>
        <p className="mt-2 text-sm text-[var(--muted)]">Tried {API_BASE}. Start everything with <code className="font-mono">scripts/run.sh</code>.</p>
        <p className="mt-2 font-mono text-xs text-[var(--muted)]">{error}</p>
      </div>
    );
  }
  if (!detail) return <div className="m-auto text-sm text-[var(--muted)]">Loading simulated match…</div>;

  return (
    <div className="mx-auto flex h-dvh w-full max-w-[1600px] flex-col gap-3 p-3 lg:p-4">
      <header className="flex items-center gap-3">
        <h1 className="text-base font-semibold tracking-tight">Beyond the Touchline</h1>
        <span className="rounded-md border border-[var(--warn)] px-2 py-0.5 text-[10px] font-bold tracking-widest text-[var(--warn)]">SIMULATED</span>
        <span className="text-xs text-[var(--muted)]">{detail.match.match_id} · synthetic events · not real match data</span>
        <Link href={`/match/${detail.match.match_id}/bench`}
          className="inline-flex items-center gap-1.5 rounded-lg border border-[var(--line)] px-2.5 py-1 text-xs hover:border-[var(--muted)]">
          {hasAlert && <span className="h-2 w-2 animate-pulse rounded-full bg-[var(--loss)]" />}
          Bench · Assistant coach →
        </Link>
        <span className="ml-auto flex items-center gap-2 text-xs text-[var(--muted)]">
          <span className={`h-2 w-2 rounded-full ${stream.connected ? "bg-[var(--live)]" : "bg-[var(--warn)]"}`} />
          {stream.connected ? "stream connected" : "connecting…"} · mode <span className="font-mono">{APP_MODE}</span>
        </span>
      </header>

      <div className="grid min-h-0 flex-1 gap-3 lg:grid-cols-[minmax(0,1fr)_380px]">
        <main className="flex min-h-0 flex-col gap-3 overflow-y-auto lg:overflow-hidden">
          <Scoreboard detail={detail} state={stream.state} clock={clock} />
          <div className="grid min-h-0 flex-1 gap-3 xl:grid-cols-[minmax(0,1fr)_320px]">
            <div className="flex min-h-0 flex-col gap-3">
              <div className="rounded-2xl border border-[var(--line)] bg-[var(--panel)] p-3">
                <Pitch detail={detail} state={stream.state} events={stream.events} highlighted={highlighted} />
              </div>
              <ReplayControls matchId={detail.match.match_id} control={stream.control} clock={clock}
                duration={detail.duration_sec} keyEvents={keyEvents} />
            </div>
            <div className="flex min-h-0 flex-col gap-3">
              <StatsPanel detail={detail} state={stream.state} />
              <EventFeed detail={detail} events={stream.events} highlightedIds={highlightedSet} onSelect={setHighlightedIds} />
            </div>
          </div>
        </main>
        <div className="min-h-[480px] lg:min-h-0">
          <AgentPanel matchId={detail.match.match_id} insights={stream.insights} provider={provider} onEvidence={setHighlightedIds} />
        </div>
      </div>
    </div>
  );
}

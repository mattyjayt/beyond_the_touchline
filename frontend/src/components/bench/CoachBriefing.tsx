"use client";

import { useEffect, useState } from "react";
import { askBriefing, type AgentAnswer } from "@/lib/api";

const EVIDENCE = /\[?(SIM-[A-Z0-9]+-E\d{4})\]?/g;

const DEBOUNCE_MS = 800;

/**
 * 3-4 sentence briefing from Claude (or the rules fallback), with clickable evidence chips.
 * It describes the second the page shows (`asofSec`, null = live) and the coach's choice.
 * Live, it refetches only when the alert, the swap or the choice changes (`liveKey`), never on
 * every clock tick; scrubbed, it follows the page's second, debounced.
 */
export function CoachBriefing({ matchId, teamId, alertSec, asofSec, liveKey, chosen, onEvidence }: {
  matchId: string;
  teamId: string;
  alertSec: number | null;
  asofSec: number | null;
  liveKey: string;
  chosen: string | null;
  onEvidence: (ids: string[]) => void;
}) {
  const [answer, setAnswer] = useState<AgentAnswer | null>(null);
  const [failed, setFailed] = useState<string | null>(null);
  const [pending, setPending] = useState(false);
  const loading = alertSec != null && (pending || (!answer && !failed));
  const trigger = asofSec === null ? liveKey : `at-${asofSec}`;

  useEffect(() => {
    if (alertSec == null) return;
    let live = true;
    const timer = setTimeout(() => {
      setPending(true);
      askBriefing(matchId, teamId, asofSec, chosen)
        .then((a) => live && (setAnswer(a), setFailed(null)))
        .catch((e) => live && setFailed(String(e)))
        .finally(() => live && setPending(false));
    }, asofSec === null ? 0 : DEBOUNCE_MS);
    return () => {
      live = false;
      clearTimeout(timer);
    };
    // asofSec only matters through `trigger` (live mode must not refetch every tick)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [matchId, teamId, alertSec, trigger, chosen]);

  const provider = answer?.provider.startsWith("claude") ? "claude" : "rules";
  return (
    <section className="col-span-12 flex flex-col gap-2 rounded-2xl border border-[var(--line)] bg-[var(--panel)] p-4">
      <div className="flex items-center gap-2">
        <h2 className="text-sm font-semibold">Briefing</h2>
        {answer && (
          <span className={`rounded-md border px-1.5 py-0.5 font-mono text-[10px] ${provider === "claude"
            ? "border-[var(--them)] text-[var(--them)]" : "border-[var(--line)] text-[var(--muted)]"}`}>{provider}</span>
        )}
        <span className="text-xs text-[var(--muted)]">does not reorder the ranking · simulated</span>
      </div>
      {alertSec == null ? (
        <p className="text-sm text-[var(--muted)]">No defender is being beaten repeatedly yet. The briefing appears when the hot-duel alert fires.</p>
      ) : loading && !answer ? (
        <p className="animate-pulse text-sm text-[var(--muted)]">Preparing the briefing…</p>
      ) : failed ? (
        <p className="text-sm text-[var(--loss)]">Briefing unavailable: {failed}</p>
      ) : answer && (
        <>
          <p className="text-sm leading-relaxed text-[var(--fg-soft)]">
            {answer.answer.split(EVIDENCE).map((part, i) =>
              i % 2 === 1 ? <Chip key={i} id={part} onClick={() => onEvidence([part])} /> : <Bold key={i} text={part} />)}
          </p>
          {answer.evidence_event_ids.length > 0 && (
            <div className="flex flex-wrap items-center gap-1.5 text-[11px] text-[var(--muted)]">
              Evidence:
              {answer.evidence_event_ids.map((id) => <Chip key={id} id={id} onClick={() => onEvidence([id])} />)}
              <button onClick={() => onEvidence(answer.evidence_event_ids)} className="underline hover:text-[var(--fg)]">show all</button>
            </div>
          )}
        </>
      )}
    </section>
  );
}

/** Claude may use **bold**; render it instead of showing the asterisks. */
function Bold({ text }: { text: string }) {
  return <>{text.split("**").map((t, i) => (i % 2 ? <strong key={i} className="text-[var(--fg)]">{t}</strong> : t))}</>;
}

function Chip({ id, onClick }: { id: string; onClick: () => void }) {
  return (
    <button onClick={onClick}
      className="mx-0.5 rounded border border-[var(--accent)] px-1 font-mono text-[10px] text-[var(--accent)] hover:bg-[var(--accent-soft)]">
      {id.split("-").pop()}
    </button>
  );
}

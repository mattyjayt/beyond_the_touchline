"use client";

import { AnimatePresence, motion } from "motion/react";
import { useState } from "react";
import { askAgent } from "@/lib/api";
import { minuteOf } from "@/lib/pitch";
import type { Insight } from "@/lib/types";

type Audience = "fan" | "analyst";

interface ChatTurn {
  id: number;
  role: "user" | "agent";
  text: string;
  evidence?: string[];
  provider?: string;
}

const KIND_LABEL: Record<Insight["kind"], string> = {
  momentum_shift: "Momentum",
  player_form: "Player form",
  tactical_alert: "Tactical",
  substitution_opportunity: "Substitution",
  key_moment: "Key moment",
};

export function AgentPanel({ matchId, insights, provider, onEvidence }: {
  matchId: string;
  insights: Insight[];
  provider: string | null;
  onEvidence: (ids: string[]) => void;
}) {
  const [audience, setAudience] = useState<Audience>("fan");
  const [chat, setChat] = useState<ChatTurn[]>([]);
  const [question, setQuestion] = useState("");
  const [busy, setBusy] = useState(false);
  const visible = insights.filter((i) => i.audience === audience).slice().reverse();

  async function ask(e: React.FormEvent) {
    e.preventDefault();
    const q = question.trim();
    if (!q || busy) return;
    setQuestion("");
    setBusy(true);
    setChat((c) => [...c, { id: Date.now(), role: "user", text: q }]);
    try {
      const res = await askAgent(matchId, q, audience);
      setChat((c) => [...c, { id: Date.now() + 1, role: "agent", text: res.answer, evidence: res.evidence_event_ids, provider: res.provider }]);
    } catch (err) {
      setChat((c) => [...c, { id: Date.now() + 1, role: "agent", text: `Agent unavailable (${String(err)}). Is the backend running?` }]);
    } finally {
      setBusy(false);
    }
  }

  return (
    <aside className="flex h-full min-h-0 flex-col rounded-2xl border border-[var(--line)] bg-[var(--panel)]">
      <header className="flex items-center justify-between gap-2 border-b border-[var(--line)] px-4 py-3">
        <div>
          <h2 className="text-sm font-semibold">Match Analyst</h2>
          <p className="text-xs text-[var(--muted)]">
            agent · <span className="font-mono">{provider ?? "…"}</span>
          </p>
        </div>
        <div className="flex rounded-lg border border-[var(--line)] p-0.5 text-xs">
          {(["fan", "analyst"] as const).map((a) => (
            <button key={a} onClick={() => setAudience(a)}
              className={`rounded-md px-2.5 py-1 capitalize ${audience === a ? "bg-[var(--fg)] text-[var(--bg)]" : "text-[var(--muted)]"}`}>
              {a}
            </button>
          ))}
        </div>
      </header>

      <div className="min-h-0 flex-1 space-y-3 overflow-y-auto p-3">
        {visible.length === 0 && chat.length === 0 && (
          <p className="px-1 pt-2 text-sm text-[var(--muted)]">
            Insights appear here as the match unfolds. Every claim links to the events behind it. Ask a question below.
          </p>
        )}
        <AnimatePresence initial={false}>
          {visible.map((i) => (
            <motion.article key={i.insight_id} layout initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }}
              className="rounded-xl border border-[var(--line)] bg-[var(--bg)] p-3">
              <div className="mb-1 flex items-center gap-2 text-[11px] text-[var(--muted)]">
                <span className="rounded bg-[var(--accent-soft)] px-1.5 py-0.5 font-medium text-[var(--accent)]">{KIND_LABEL[i.kind]}</span>
                <span className="font-mono">{minuteOf(i.asof_sec)}&apos;</span>
                <span className="ml-auto font-mono">{i.generator_version}</span>
              </div>
              <h3 className="text-sm font-semibold leading-snug">{i.headline}</h3>
              <p className="mt-1 text-sm leading-relaxed text-[var(--fg-soft)]">{i.explanation}</p>
              <Evidence ids={i.evidence_event_ids} onEvidence={onEvidence} />
              <p className="mt-2 text-[11px] italic text-[var(--muted)]">Uncertainty: {i.uncertainty}</p>
            </motion.article>
          ))}
        </AnimatePresence>
        {chat.map((t) => (
          <div key={t.id} className={`rounded-xl px-3 py-2 text-sm ${t.role === "user" ? "ml-8 bg-[var(--line)]" : "mr-4 border border-[var(--line)]"}`}>
            <p className="whitespace-pre-wrap leading-relaxed">{t.text}</p>
            {t.evidence && t.evidence.length > 0 && <Evidence ids={t.evidence} onEvidence={onEvidence} />}
            {t.provider && <p className="mt-1 font-mono text-[10px] text-[var(--muted)]">{t.provider}</p>}
          </div>
        ))}
        {busy && <p className="px-1 text-xs text-[var(--muted)]">Analyst is checking the evidence…</p>}
      </div>

      <form onSubmit={ask} className="border-t border-[var(--line)] p-3">
        <div className="flex gap-2">
          <input value={question} onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask about the match… e.g. Should Arsenal change the right wing?"
            className="h-10 min-w-0 flex-1 rounded-lg border border-[var(--line)] bg-[var(--bg)] px-3 text-sm outline-none focus:border-[var(--accent)]" />
          <button disabled={busy} className="h-10 rounded-lg bg-[var(--accent)] px-4 text-sm font-semibold text-black disabled:opacity-50">
            Ask
          </button>
        </div>
        <p className="mt-2 text-[10px] text-[var(--muted)]">Simulated match. AI analysis cites synthetic events and may be uncertain.</p>
      </form>
    </aside>
  );
}

function Evidence({ ids, onEvidence }: { ids: string[]; onEvidence: (ids: string[]) => void }) {
  return (
    <div className="mt-2 flex flex-wrap items-center gap-1">
      <button onClick={() => onEvidence(ids)} className="text-[11px] text-[var(--accent)] hover:underline">evidence</button>
      {ids.slice(0, 8).map((id) => (
        <button key={id} onClick={() => onEvidence([id])}
          className="rounded border border-[var(--line)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--muted)] hover:border-[var(--accent)] hover:text-[var(--fg)]">
          {id.split("-").pop()}
        </button>
      ))}
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import { CoachBriefing } from "@/components/bench/CoachBriefing";
import { CoachHeader } from "@/components/bench/CoachHeader";
import { DuelWinRate } from "@/components/bench/DuelWinRate";
import { FlankPitch } from "@/components/bench/FlankPitch";
import { FormationPreview } from "@/components/bench/FormationPreview";
import { OptionCards } from "@/components/bench/OptionCards";
import { RadarCompare } from "@/components/bench/RadarCompare";
import { SprintRace } from "@/components/bench/SprintRace";
import { SwapImpact } from "@/components/bench/SwapImpact";
import { VariableImportance } from "@/components/bench/VariableImportance";
import { useBenchView } from "@/hooks/useBenchView";
import { API_BASE, fetchMatch } from "@/lib/api";
import { incoming, optionKey } from "@/lib/bench";
import { PALETTE } from "@/lib/chart";
import type { MatchDetail, RadarAxis } from "@/lib/types";

export function BenchPage({ matchId }: { matchId: string }) {
  const [detail, setDetail] = useState<MatchDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    fetchMatch(matchId).then(setDetail).catch((e) => setError(String(e)));
  }, [matchId]);

  if (error) {
    return (
      <div className="m-auto max-w-md p-8 text-center">
        <h1 className="text-lg font-semibold">Match not available</h1>
        <p className="mt-2 text-sm text-[var(--muted)]">Tried {API_BASE} for {matchId}. Start everything with <code className="font-mono">scripts/run.sh</code>.</p>
        <p className="mt-2 font-mono text-xs text-[var(--muted)]">{error}</p>
      </div>
    );
  }
  if (!detail) return <div className="m-auto text-sm text-[var(--muted)]">Loading simulated match…</div>;
  return <BenchBody detail={detail} />;
}

/** The home team's assistant coach (spec non-goal: no away-team advisor UI). */
function BenchBody({ detail }: { detail: MatchDetail }) {
  const { match, home } = detail;
  const b = useBenchView(match.match_id, match.home_team_id);
  const { view } = b;
  const [highlight, setHighlight] = useState<string[]>([]);
  const [highlightVar, setHighlightVar] = useState<RadarAxis | null>(null);

  const name = (id: string) => detail.players[id]?.display_name ?? view?.cards[id]?.name ?? id;
  const options = view?.options ?? [];
  const selected = options.find((o) => optionKey(o) === b.selected)
    ?? options.find((o) => o.option_type !== "keep") ?? null;
  const candId = incoming(selected);
  const candidate = (candId && view?.cards[candId]) || view?.defender || null;
  const tormentorId = view?.tormentor?.player_id;
  const defenderId = view?.defender?.player_id;
  const raceIds = [...new Set([tormentorId, defenderId, candId].filter((x): x is string => !!x))];
  const colours: Record<string, string> = {};
  if (tormentorId) colours[tormentorId] = PALETTE.them;
  if (defenderId) colours[defenderId] = PALETTE.ghost;
  if (candId) colours[candId] = PALETTE.us;

  return (
    <div className="mx-auto grid w-full max-w-[1600px] grid-cols-12 gap-3 p-3 lg:p-4">
      <CoachHeader detail={detail} view={view} asof={b.asof} clock={b.clock} onAsof={b.setAsof} />
      {b.error && <p className="col-span-12 text-xs text-[var(--loss)]">Bench view unavailable: {b.error}</p>}
      {!view ? (
        <p className="col-span-12 py-10 text-center text-sm text-[var(--muted)]">Loading the bench view…</p>
      ) : (
        <>
          <CoachBriefing matchId={match.match_id} teamId={match.home_team_id}
            alertSec={view.alert?.first_fired_sec ?? null} chosen={b.chosen} onEvidence={setHighlight} />
          <FlankPitch ledger={view.ledger} swapSec={view.impact?.swap_sec ?? null} highlight={highlight}
            onHighlight={setHighlight} name={name} />
          <DuelWinRate ledger={view.ledger} alertSec={view.alert?.first_fired_sec ?? null}
            swapSec={view.impact?.swap_sec ?? null} onSeek={b.setAsof} />
          <OptionCards options={options} selected={selected ? optionKey(selected) : null} chosen={b.chosen}
            onSelect={b.select} onChoose={b.choose} name={name} />
          <RadarCompare tormentor={view.tormentor} candidate={candidate} current={view.defender}
            highlightVar={highlightVar} onHighlightVar={setHighlightVar} />
          <SprintRace race={view.race} ids={raceIds} colours={colours} />
          <SwapImpact impact={view.impact} executedRank={view.executed_option_rank_at_alert} name={name} />
          <FormationPreview formation={match.home_formation} slots={view.slots} option={selected}
            players={detail.players} kit={home.primary_color} ink={home.secondary_color} />
          <VariableImportance items={view.importance} note={view.importance_note}
            highlightVar={highlightVar} onHighlightVar={setHighlightVar} />
        </>
      )}
    </div>
  );
}

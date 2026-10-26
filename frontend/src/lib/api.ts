import type { BenchView, MatchDetail, ReplayControl } from "./types";

export const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
export const APP_MODE = process.env.NEXT_PUBLIC_APP_MODE ?? "local";

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return (await res.json()) as T;
}

export const fetchDemoMatch = () =>
  fetch(`${API_BASE}/api/matches/demo`).then((r) => json<MatchDetail>(r));

export const fetchMatch = (matchId: string) =>
  fetch(`${API_BASE}/api/matches/${matchId}`).then((r) => json<MatchDetail>(r));

export const fetchHealth = () =>
  fetch(`${API_BASE}/health`).then((r) =>
    json<{ status: string; mode: string; agent_provider: string }>(r),
  );

export type ReplayAction = "play" | "pause" | "speed" | "seek" | "restart";

export const controlReplay = (matchId: string, action: ReplayAction, value?: number) =>
  fetch(`${API_BASE}/api/matches/${matchId}/replay`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ action, value }),
  }).then((r) => json<ReplayControl>(r));

export const fetchBench = (matchId: string, teamId: string, asofSec?: number | null) => {
  const q = new URLSearchParams({ team_id: teamId });
  if (asofSec != null) q.set("asof_sec", String(Math.round(asofSec)));
  return fetch(`${API_BASE}/api/matches/${matchId}/bench?${q}`).then((r) => json<BenchView>(r));
};

export const streamUrl = (matchId: string) => `${API_BASE}/api/matches/${matchId}/stream`;

export interface AgentAnswer {
  answer: string;
  evidence_event_ids: string[];
  provider: string;
  synthetic: true;
}

export const askAgent = (matchId: string, question: string, audience: "fan" | "analyst") =>
  fetch(`${API_BASE}/api/agent/ask`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ match_id: matchId, question, audience }),
  }).then((r) => json<AgentAnswer>(r));

/** Assistant-coach briefing: Claude when available, else the deterministic rules text. */
export const askBriefing = (matchId: string, teamId: string) =>
  fetch(`${API_BASE}/api/agent/ask`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ match_id: matchId, team_id: teamId, mode: "briefing", question: "" }),
  }).then((r) => json<AgentAnswer>(r));

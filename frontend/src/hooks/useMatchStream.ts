"use client";

import { useEffect, useReducer } from "react";
import { streamUrl } from "@/lib/api";
import type { Insight, MatchEvent, MatchState, ReplayControl, StreamMessage } from "@/lib/types";

export interface StreamState {
  connected: boolean;
  control: ReplayControl | null;
  events: MatchEvent[];
  state: MatchState | null;
  insights: Insight[];
}

type Action = { type: "connected"; value: boolean } | StreamMessage;

const initial: StreamState = { connected: false, control: null, events: [], state: null, insights: [] };

function reducer(s: StreamState, a: Action): StreamState {
  switch (a.type) {
    case "connected": return { ...s, connected: a.value };
    case "snapshot": return { ...s, ...a.data, insights: a.data.insights };
    case "event": return { ...s, events: [...s.events, a.data] };
    case "state": return { ...s, state: a.data };
    case "control": return { ...s, control: a.data };
    case "insight":
      return s.insights.some((i) => i.insight_id === a.data.insight_id)
        ? s
        : { ...s, insights: [...s.insights, a.data] };
    case "recommendation": return s;
  }
}

export function useMatchStream(matchId: string | null): StreamState {
  const [state, dispatch] = useReducer(reducer, initial);

  useEffect(() => {
    if (!matchId) return;
    const es = new EventSource(streamUrl(matchId));
    es.onopen = () => dispatch({ type: "connected", value: true });
    es.onerror = () => dispatch({ type: "connected", value: false });
    es.onmessage = (e) => dispatch(JSON.parse(e.data) as StreamMessage);
    return () => es.close();
  }, [matchId]);

  return state;
}

/** Match clock: the server replay clock, advanced by every streamed event. */
export function matchClock({ control, events }: StreamState): number {
  const lastEventSec = events.length ? events[events.length - 1].event_sec : 0;
  return Math.max(control?.clock_sec ?? 0, lastEventSec);
}

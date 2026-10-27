"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { matchClock, useMatchStream } from "@/hooks/useMatchStream";
import { fetchBench } from "@/lib/api";
import type { BenchView } from "@/lib/types";

const LIVE_REFETCH_MS = 2000;
const choiceKey = (matchId: string) => `btt-bench-choice-${matchId}`;

function readChoice(matchId: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return window.localStorage.getItem(choiceKey(matchId));
  } catch {
    return null; // storage unavailable (private mode): the choice simply isn't remembered
  }
}

/**
 * Assistant-coach view for one team. `asof === null` follows the live replay clock (refetch
 * throttled to every 2 s); a number pins the view to that second (refetch at once). Options
 * are tracked by `optionKey` (stable across refetches), not by rec_id. The coach's choice is
 * logged client-side only.
 */
export function useBenchView(matchId: string, teamId: string) {
  const stream = useMatchStream(matchId);
  const clock = Math.floor(matchClock(stream));
  const [asof, setAsofState] = useState<number | null>(null);
  const [view, setView] = useState<BenchView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  // Lazy read: nothing that shows the choice renders before the first client-side fetch,
  // so the server render (null) never disagrees with the hydrated value.
  const [chosen, setChosen] = useState<string | null>(() => readChoice(matchId));
  const lastFetch = useRef(0);
  const request = useRef(0);

  const target = asof ?? clock;
  useEffect(() => {
    const wait = asof === null ? Math.max(0, LIVE_REFETCH_MS - (Date.now() - lastFetch.current)) : 0;
    const timer = setTimeout(() => {
      lastFetch.current = Date.now();
      const id = ++request.current;
      fetchBench(matchId, teamId, asof)
        .then((v) => {
          if (id !== request.current) return; // a newer request superseded this one
          setView(v);
          setError(null);
        })
        .catch((e) => setError(String(e)));
    }, wait);
    return () => clearTimeout(timer);
  }, [matchId, teamId, asof, target]);

  const choose = useCallback(
    (key: string | null) => {
      setChosen(key);
      try {
        if (key) window.localStorage.setItem(choiceKey(matchId), key);
        else window.localStorage.removeItem(choiceKey(matchId));
      } catch {
        // ignore storage failures
      }
    },
    [matchId],
  );

  const setAsof = useCallback((sec: number | null) => setAsofState(sec), []);

  return { view, error, asof, setAsof, clock, stream, selected, select: setSelected, chosen, choose };
}

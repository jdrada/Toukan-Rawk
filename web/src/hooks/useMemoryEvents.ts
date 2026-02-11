"use client";

import { useEffect, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";
const POLL_INTERVAL = 3000;

/**
 * Hook that keeps memories up-to-date via polling.
 * Tries SSE first; if SSE fails or returns 503, falls back to polling.
 * Polling only runs when there are memories in a pending state.
 */
export function useMemoryEvents(hasPendingMemories: boolean) {
  const queryClient = useQueryClient();
  const sseRef = useRef<EventSource | null>(null);
  const sseFailedRef = useRef(false);

  // Try SSE connection once
  useEffect(() => {
    const es = new EventSource(`${API_URL}/events/memories`);
    sseRef.current = es;

    es.addEventListener("memory-update", (event) => {
      try {
        const data = JSON.parse(event.data);
        queryClient.invalidateQueries({ queryKey: ["memories"] });
        if (data.memory_id) {
          queryClient.invalidateQueries({ queryKey: ["memory", data.memory_id] });
        }
      } catch {}
    });

    es.addEventListener("error", () => {
      // SSE not available (Redis disabled), switch to polling
      sseFailedRef.current = true;
      es.close();
      sseRef.current = null;
    });

    return () => {
      es.close();
      sseRef.current = null;
    };
  }, [queryClient]);

  // Polling fallback: only when SSE failed and there are pending memories
  useEffect(() => {
    if (!sseFailedRef.current || !hasPendingMemories) return;

    const interval = setInterval(() => {
      queryClient.invalidateQueries({ queryKey: ["memories"] });
    }, POLL_INTERVAL);

    return () => clearInterval(interval);
  }, [queryClient, hasPendingMemories]);
}

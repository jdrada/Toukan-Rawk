"use client";

import { useEffect, useState } from "react";
import { useQueryClient } from "@tanstack/react-query";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";
const SLOW_POLL = 1000; // 1s — catch new memories
const FAST_POLL = 1000;  // 1s — track processing status

/**
 * Hook that keeps memories up-to-date.
 * Tries SSE first; if it fails, falls back to polling.
 * Polls every 10s normally, every 3s when memories are processing.
 */
export function useMemoryEvents(hasPendingMemories: boolean) {
  const queryClient = useQueryClient();
  const [usePolling, setUsePolling] = useState(false);

  // Try SSE connection once
  useEffect(() => {
    const es = new EventSource(`${API_URL}/events/memories`);

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
      es.close();
      setUsePolling(true);
    });

    return () => {
      es.close();
    };
  }, [queryClient]);

  // Polling fallback — always active when SSE is down
  useEffect(() => {
    if (!usePolling) return;

    const interval = setInterval(() => {
      queryClient.invalidateQueries({ queryKey: ["memories"] });
    }, hasPendingMemories ? FAST_POLL : SLOW_POLL);

    return () => clearInterval(interval);
  }, [queryClient, usePolling, hasPendingMemories]);
}

"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Global EventSource instance shared across all components
let globalEventSource: EventSource | null = null;
let connectionCount = 0;
let queryClientRef: ReturnType<typeof useQueryClient> | null = null;

/**
 * Hook that establishes a SHARED Server-Sent Events connection to receive real-time memory updates.
 * Only creates ONE connection regardless of how many components use this hook.
 * Automatically invalidates TanStack Query cache when updates arrive.
 *
 * Detects:
 * - New memories being created/uploaded
 * - Status changes (uploading → processing → ready/failed)
 * - Any updates to existing memories
 */
export function useMemoryEvents() {
  const queryClient = useQueryClient();

  useEffect(() => {
    connectionCount++;
    queryClientRef = queryClient;

    console.log(`[SSE] Component mounted (active connections: ${connectionCount})`);

    // Create EventSource only if it doesn't exist yet
    if (!globalEventSource) {
      console.log("[SSE] Creating new EventSource connection...");
      globalEventSource = new EventSource(`${API_URL}/events/memories`);

      // Listen for memory-update events
      globalEventSource.addEventListener("memory-update", (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log("[SSE] Memory update received:", data);

          // Use the stored queryClient reference to invalidate queries
          if (queryClientRef) {
            // Invalidate all memory queries to trigger refetch
            queryClientRef.invalidateQueries({ queryKey: ["memories"] });

            // Also invalidate the specific memory detail query
            if (data.memory_id) {
              queryClientRef.invalidateQueries({
                queryKey: ["memory", data.memory_id]
              });
            }
          }
        } catch (error) {
          console.error("[SSE] Failed to parse memory-update event:", error);
        }
      });

      // Handle connection open
      globalEventSource.addEventListener("open", () => {
        console.log("[SSE] ✅ Connection established");
      });

      // Handle errors
      globalEventSource.addEventListener("error", (error) => {
        console.error("[SSE] Connection error:", error);
        // EventSource automatically attempts to reconnect
      });
    } else {
      console.log("[SSE] Reusing existing EventSource connection");
    }

    // Cleanup: only close connection when last component unmounts
    return () => {
      connectionCount--;
      console.log(`[SSE] Component unmounted (active connections: ${connectionCount})`);

      if (connectionCount === 0 && globalEventSource) {
        console.log("[SSE] Closing EventSource connection (no more listeners)");
        globalEventSource.close();
        globalEventSource = null;
        queryClientRef = null;
      }
    };
  }, [queryClient]);
}

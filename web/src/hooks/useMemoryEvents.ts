"use client";

import { useEffect } from "react";
import { useQueryClient } from "@tanstack/react-query";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Hook that establishes a Server-Sent Events connection to receive real-time memory updates.
 * Automatically invalidates TanStack Query cache when updates arrive, eliminating the need for polling.
 */
export function useMemoryEvents() {
  const queryClient = useQueryClient();

  useEffect(() => {
    // Create EventSource connection to SSE endpoint
    const eventSource = new EventSource(`${API_URL}/events/memories`);

    // Listen for memory-update events
    eventSource.addEventListener("memory-update", (event) => {
      try {
        // Parse the event data (backend sends JSON with memory ID and status)
        const data = JSON.parse(event.data);
        console.log("[SSE] Memory update received:", data);

        // Invalidate all memory queries to trigger refetch
        queryClient.invalidateQueries({ queryKey: ["memories"] });

        // If we have a specific memory ID, also invalidate that detail query
        if (data.memory_id) {
          queryClient.invalidateQueries({ queryKey: ["memory", data.memory_id] });
        }
      } catch (error) {
        console.error("[SSE] Failed to parse memory-update event:", error);
      }
    });

    // Handle connection open
    eventSource.addEventListener("open", () => {
      console.log("[SSE] Connection established");
    });

    // Handle errors
    eventSource.addEventListener("error", (error) => {
      console.error("[SSE] Connection error:", error);
      // EventSource automatically attempts to reconnect
    });

    // Cleanup on unmount
    return () => {
      console.log("[SSE] Closing connection");
      eventSource.close();
    };
  }, [queryClient]);
}

"use client";

import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "next/navigation";
import { getMemories } from "@/lib/api";
import { MemoryCard } from "@/components/memories/memory-card";
import { Skeleton } from "@/components/ui/skeleton";
import { Pagination } from "@/components/memories/pagination";
import { MemoryStatus } from "@/types/memory";

const PAGE_SIZE = 12;

export function MemoriesList() {
  const searchParams = useSearchParams();
  const page = Math.max(1, parseInt(searchParams.get("page") || "1", 10));
  const search = searchParams.get("search") || undefined;
  const status = searchParams.get("status") || undefined;

  const { data, isLoading, error } = useQuery({
    queryKey: ["memories", { page, search, status }],
    queryFn: () => getMemories({ page, page_size: PAGE_SIZE, search, status }),
    refetchInterval: (query) => {
      // Auto-refetch every 2 seconds if there are any processing/uploading memories
      const hasProcessingMemories = query.state.data?.items.some(
        (memory) =>
          memory.status === MemoryStatus.PROCESSING ||
          memory.status === MemoryStatus.UPLOADING
      );
      return hasProcessingMemories ? 2000 : false;
    },
  });

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="rounded-full bg-destructive/10 p-4 mb-4">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-destructive"
          >
            <circle cx="12" cy="12" r="10" />
            <line x1="12" x2="12" y1="8" y2="12" />
            <line x1="12" x2="12.01" y1="16" y2="16" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold">Failed to load memories</h3>
        <p className="text-sm text-muted-foreground max-w-sm mt-1">
          {error instanceof Error ? error.message : "An error occurred"}
        </p>
      </div>
    );
  }

  if (isLoading) {
    return <MemoryGridSkeleton />;
  }

  if (!data || data.items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center">
        <div className="rounded-full bg-muted p-4 mb-4">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-muted-foreground"
          >
            <path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z" />
            <path d="M19 10v2a7 7 0 0 1-14 0v-2" />
            <line x1="12" x2="12" y1="19" y2="22" />
          </svg>
        </div>
        <h3 className="text-lg font-semibold">No memories yet</h3>
        <p className="text-sm text-muted-foreground max-w-sm mt-1">
          {search || status
            ? "No memories match your filters. Try a different search or status."
            : "Record your first meeting using the mobile app and it will show up here."}
        </p>
      </div>
    );
  }

  const totalPages = Math.ceil(data.total / PAGE_SIZE);

  return (
    <>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {data.items.map((memory) => (
          <MemoryCard key={memory.id} memory={memory} />
        ))}
      </div>
      <Pagination page={page} totalPages={totalPages} total={data.total} />
    </>
  );
}

function MemoryGridSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <div key={i} className="space-y-3 rounded-lg border p-4">
          <div className="flex items-start justify-between">
            <Skeleton className="h-5 w-3/4" />
            <Skeleton className="h-5 w-16" />
          </div>
          <Skeleton className="h-3 w-1/3" />
          <Skeleton className="h-12 w-full" />
        </div>
      ))}
    </div>
  );
}

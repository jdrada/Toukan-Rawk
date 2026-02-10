import { Suspense } from "react";
import { getMemories } from "@/lib/api";
import { MemoryCard } from "@/components/memories/memory-card";
import { SearchBar } from "@/components/memories/search-bar";
import { Pagination } from "@/components/memories/pagination";
import { Skeleton } from "@/components/ui/skeleton";

const PAGE_SIZE = 12;

interface Props {
  searchParams: Promise<{ page?: string; search?: string; status?: string }>;
}

export default async function MemoriesPage({ searchParams }: Props) {
  const params = await searchParams;
  const page = Math.max(1, parseInt(params.page || "1", 10));
  const search = params.search || undefined;
  const status = params.status || undefined;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Memories</h1>
        <p className="text-muted-foreground">
          Your recorded meetings, transcribed and summarized.
        </p>
      </div>
      <Suspense fallback={<SearchBarFallback />}>
        <SearchBar />
      </Suspense>
      <Suspense fallback={<MemoryGridSkeleton />}>
        <MemoryGrid page={page} search={search} status={status} />
      </Suspense>
    </div>
  );
}

async function MemoryGrid({
  page,
  search,
  status,
}: {
  page: number;
  search?: string;
  status?: string;
}) {
  const data = await getMemories({ page, page_size: PAGE_SIZE, search, status });
  const totalPages = Math.ceil(data.total / PAGE_SIZE);

  if (data.items.length === 0) {
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

function SearchBarFallback() {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
      <Skeleton className="h-10 flex-1" />
      <Skeleton className="h-10 w-[140px]" />
    </div>
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

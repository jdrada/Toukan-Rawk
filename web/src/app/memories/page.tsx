import { Suspense } from "react";
import { SearchBar } from "@/components/memories/search-bar";
import { MemoriesList } from "@/components/memories/memories-list";
import { Skeleton } from "@/components/ui/skeleton";

export default function MemoriesPage() {
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
      <MemoriesList />
    </div>
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

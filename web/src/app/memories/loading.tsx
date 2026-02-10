import { Skeleton } from "@/components/ui/skeleton";

export default function MemoriesLoading() {
  return (
    <div className="space-y-6">
      <div>
        <Skeleton className="h-8 w-40" />
        <Skeleton className="mt-2 h-4 w-64" />
      </div>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <Skeleton className="h-10 flex-1" />
        <Skeleton className="h-10 w-[140px]" />
      </div>
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
    </div>
  );
}

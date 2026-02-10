import { Skeleton } from "@/components/ui/skeleton";

export default function MemoryDetailLoading() {
  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      <Skeleton className="h-4 w-32" />
      <div className="space-y-2">
        <Skeleton className="h-8 w-2/3" />
        <Skeleton className="h-4 w-48" />
      </div>
      <Skeleton className="h-px w-full" />
      {/* Summary card skeleton */}
      <div className="rounded-lg border p-6 space-y-3">
        <Skeleton className="h-5 w-24" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-full" />
        <Skeleton className="h-4 w-3/4" />
      </div>
      {/* Key points card skeleton */}
      <div className="rounded-lg border p-6 space-y-3">
        <Skeleton className="h-5 w-32" />
        <Skeleton className="h-4 w-5/6" />
        <Skeleton className="h-4 w-4/6" />
        <Skeleton className="h-4 w-5/6" />
      </div>
    </div>
  );
}

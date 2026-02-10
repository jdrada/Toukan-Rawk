"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function MemoryDetailError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center max-w-3xl mx-auto">
      <h2 className="text-lg font-semibold">Failed to load memory</h2>
      <p className="mt-2 text-sm text-muted-foreground max-w-sm">
        {error.message || "Something went wrong while loading this memory."}
      </p>
      <div className="mt-4 flex gap-2">
        <Button variant="outline" onClick={reset}>
          Try again
        </Button>
        <Button variant="ghost" asChild>
          <Link href="/memories">Back to memories</Link>
        </Button>
      </div>
    </div>
  );
}

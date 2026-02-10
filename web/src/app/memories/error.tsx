"use client";

import { Button } from "@/components/ui/button";

export default function MemoriesError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <h2 className="text-lg font-semibold">Something went wrong</h2>
      <p className="mt-2 text-sm text-muted-foreground max-w-sm">
        {error.message || "Failed to load memories. The backend may be unavailable."}
      </p>
      <Button variant="outline" onClick={reset} className="mt-4">
        Try again
      </Button>
    </div>
  );
}

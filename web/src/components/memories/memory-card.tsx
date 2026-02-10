"use client";

import Link from "next/link";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/ui/status-badge";
import { ProgressIndicator } from "@/components/ui/progress-indicator";
import { Button } from "@/components/ui/button";
import { MemoryResponse, MemoryStatus } from "@/types/memory";
import { retryMemoryProcessing } from "@/lib/api";
import { RefreshCw } from "lucide-react";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
}

export function MemoryCard({ memory }: { memory: MemoryResponse }) {
  const queryClient = useQueryClient();
  const title = memory.title || "Untitled Memory";
  const summary =
    memory.summary && memory.summary.length > 150
      ? memory.summary.slice(0, 150) + "..."
      : memory.summary;

  const retryMutation = useMutation({
    mutationFn: () => retryMemoryProcessing(memory.id),
    onSuccess: () => {
      // Invalidate all memory queries to trigger refetch
      queryClient.invalidateQueries({ queryKey: ["memories"] });
    },
  });

  const handleRetry = (e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    retryMutation.mutate();
  };

  const showProgress =
    memory.status === MemoryStatus.UPLOADING ||
    memory.status === MemoryStatus.PROCESSING;

  return (
    <Link href={`/memories/${memory.id}`} className="block">
      <Card className="transition-colors hover:bg-accent/50">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-base font-semibold leading-snug">
              {title}
            </CardTitle>
            <StatusBadge status={memory.status as MemoryStatus} />
          </div>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <time>{formatDate(memory.created_at)}</time>
            {memory.duration && (
              <>
                <span>&middot;</span>
                <span>{formatDuration(memory.duration)}</span>
              </>
            )}
          </div>
        </CardHeader>
        {showProgress && (
          <CardContent className="pt-0">
            <ProgressIndicator status={memory.status as MemoryStatus} />
          </CardContent>
        )}
        {summary && (
          <CardContent className="pt-0">
            <p className="text-sm text-muted-foreground leading-relaxed">
              {summary}
            </p>
          </CardContent>
        )}
        {memory.key_points && memory.key_points.length > 0 && (
          <CardContent className="pt-0">
            <p className="text-xs text-muted-foreground">
              {memory.key_points.length} key point{memory.key_points.length !== 1 ? "s" : ""}
            </p>
          </CardContent>
        )}
        {memory.status === MemoryStatus.FAILED && (
          <CardContent className="pt-0">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRetry}
              disabled={retryMutation.isPending}
              className="w-full text-xs"
            >
              <RefreshCw className={`h-3 w-3 mr-1 ${retryMutation.isPending ? "animate-spin" : ""}`} />
              {retryMutation.isPending ? "Retrying..." : "Retry Processing"}
            </Button>
          </CardContent>
        )}
      </Card>
    </Link>
  );
}

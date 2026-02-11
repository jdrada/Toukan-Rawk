"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useRouter } from "next/navigation";
import { ArrowLeft, Clock, Calendar, Lightbulb, ListChecks, Trash2, RefreshCw } from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { StatusBadge } from "@/components/ui/status-badge";
import { ProgressIndicator } from "@/components/ui/progress-indicator";
import { TranscriptSection } from "@/components/memories/transcript-section";
import { Button } from "@/components/ui/button";
import { MemoryStatus } from "@/types/memory";
import { getMemory, deleteMemory, retryMemoryProcessing } from "@/lib/api";
import { useState } from "react";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  if (mins >= 60) {
    const hrs = Math.floor(mins / 60);
    const remainMins = mins % 60;
    return `${hrs}h ${remainMins}m`;
  }
  return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
}

interface MemoryDetailClientProps {
  id: string;
}

export function MemoryDetailClient({ id }: MemoryDetailClientProps) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const { data: memory, isLoading, error } = useQuery({
    queryKey: ["memory", id],
    queryFn: () => getMemory(id),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === MemoryStatus.UPLOADING || status === MemoryStatus.PROCESSING) {
        return 3_000;
      }
      return false;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: () => deleteMemory(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memories"] });
      router.push("/memories");
    },
  });

  const retryMutation = useMutation({
    mutationFn: () => retryMemoryProcessing(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["memory", id] });
      queryClient.invalidateQueries({ queryKey: ["memories"] });
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
        <h3 className="text-lg font-semibold">Failed to load memory</h3>
        <p className="text-sm text-muted-foreground max-w-sm mt-1">
          {error instanceof Error ? error.message : "An error occurred"}
        </p>
        <Link href="/memories" className="mt-4">
          <Button variant="outline">Back to memories</Button>
        </Link>
      </div>
    );
  }

  if (isLoading || !memory) {
    return (
      <div className="space-y-6 max-w-3xl mx-auto animate-pulse">
        <div className="h-4 bg-muted rounded w-32" />
        <div className="h-8 bg-muted rounded w-3/4" />
        <div className="h-4 bg-muted rounded w-1/2" />
      </div>
    );
  }

  const title = memory.title || "Untitled Memory";
  const showProgress =
    memory.status === MemoryStatus.UPLOADING || memory.status === MemoryStatus.PROCESSING;

  return (
    <div className="space-y-6 max-w-3xl mx-auto">
      {/* Back link */}
      <Link
        href="/memories"
        className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        Back to memories
      </Link>

      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-start justify-between gap-3">
          <h1 className="text-2xl font-bold tracking-tight">{title}</h1>
          <div className="flex items-center gap-2">
            <StatusBadge status={memory.status as MemoryStatus} />
            {!showDeleteConfirm && (
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowDeleteConfirm(true)}
                className="text-muted-foreground hover:text-destructive"
              >
                <Trash2 className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
        {showDeleteConfirm && (
          <div className="flex items-center gap-2 p-3 bg-destructive/10 rounded-lg">
            <p className="text-sm text-destructive flex-1">Delete this memory permanently?</p>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowDeleteConfirm(false)}
              disabled={deleteMutation.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
            >
              {deleteMutation.isPending ? "Deleting..." : "Delete"}
            </Button>
          </div>
        )}
        <div className="flex flex-wrap items-center gap-4 text-sm text-muted-foreground">
          <span className="inline-flex items-center gap-1.5">
            <Calendar className="h-4 w-4" />
            {formatDate(memory.created_at)}
          </span>
          {memory.duration && (
            <span className="inline-flex items-center gap-1.5">
              <Clock className="h-4 w-4" />
              {formatDuration(memory.duration)}
            </span>
          )}
        </div>
      </div>

      <Separator />

      {/* Progress */}
      {showProgress && (
        <Card>
          <CardContent className="pt-6">
            <ProgressIndicator status={memory.status as MemoryStatus} />
          </CardContent>
        </Card>
      )}

      {/* Summary */}
      {memory.summary && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Summary</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-relaxed">{memory.summary}</p>
          </CardContent>
        </Card>
      )}

      {/* Key Points */}
      {memory.key_points && memory.key_points.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg inline-flex items-center gap-2">
              <Lightbulb className="h-5 w-5" />
              Key Points
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {memory.key_points.map((point, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="mt-1 h-1.5 w-1.5 rounded-full bg-[var(--orange-500)] shrink-0" />
                  {point}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Action Items */}
      {memory.action_items && memory.action_items.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg inline-flex items-center gap-2">
              <ListChecks className="h-5 w-5" />
              Action Items
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {memory.action_items.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <span className="mt-0.5 h-4 w-4 rounded border border-muted-foreground/40 shrink-0" />
                  {item}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Transcript */}
      {memory.transcript && <TranscriptSection transcript={memory.transcript} />}

      {/* Failed state with retry */}
      {memory.status === MemoryStatus.FAILED && (
        <Card className="border-destructive/50">
          <CardContent className="py-8 text-center space-y-3">
            <p className="text-sm text-destructive">
              Processing failed for this memory. The audio file has been saved and can be re-processed.
            </p>
            <Button
              variant="outline"
              onClick={() => retryMutation.mutate()}
              disabled={retryMutation.isPending}
              className="mx-auto"
            >
              <RefreshCw className={`h-4 w-4 mr-2 ${retryMutation.isPending ? "animate-spin" : ""}`} />
              {retryMutation.isPending ? "Retrying..." : "Retry Processing"}
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

import { ArrowLeft, Clock, Calendar, Lightbulb, ListChecks } from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { StatusBadge } from "@/components/ui/status-badge";
import { TranscriptSection } from "@/components/memories/transcript-section";
import { MemoryResponse, MemoryStatus } from "@/types/memory";

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

export function MemoryDetail({ memory }: { memory: MemoryResponse }) {
  const title = memory.title || "Untitled Memory";

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
          <StatusBadge status={memory.status as MemoryStatus} />
        </div>
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
                  <span className="mt-1 h-1.5 w-1.5 rounded-full bg-primary shrink-0" />
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

      {/* Processing state */}
      {memory.status === MemoryStatus.PROCESSING && (
        <Card className="border-dashed">
          <CardContent className="py-8 text-center">
            <p className="text-sm text-muted-foreground">
              This memory is still being processed. Summary and key points will appear once ready.
            </p>
          </CardContent>
        </Card>
      )}

      {memory.status === MemoryStatus.FAILED && (
        <Card className="border-destructive/50">
          <CardContent className="py-8 text-center">
            <p className="text-sm text-destructive">
              Processing failed for this memory. The audio file has been saved and can be re-processed.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

"use client";

import { useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";

export function TranscriptSection({ transcript }: { transcript: string }) {
  const [expanded, setExpanded] = useState(false);
  const isLong = transcript.length > 500;
  const displayText = !expanded && isLong ? transcript.slice(0, 500) + "..." : transcript;

  return (
    <div className="space-y-3">
      <h2 className="text-lg font-semibold">Full Transcript</h2>
      <div className="rounded-lg border bg-muted/50 p-4">
        <p className="text-sm leading-relaxed whitespace-pre-wrap">{displayText}</p>
      </div>
      {isLong && (
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setExpanded(!expanded)}
          className="gap-1"
        >
          {expanded ? (
            <>
              Show less <ChevronUp className="h-4 w-4" />
            </>
          ) : (
            <>
              Show full transcript <ChevronDown className="h-4 w-4" />
            </>
          )}
        </Button>
      )}
    </div>
  );
}

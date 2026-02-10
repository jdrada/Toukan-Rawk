import { Badge } from "@/components/ui/badge";
import { MemoryStatus } from "@/types/memory";

const statusConfig: Record<
  MemoryStatus,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline" }
> = {
  [MemoryStatus.READY]: { label: "Ready", variant: "default" },
  [MemoryStatus.PROCESSING]: { label: "Processing", variant: "secondary" },
  [MemoryStatus.UPLOADING]: { label: "Uploading", variant: "outline" },
  [MemoryStatus.FAILED]: { label: "Failed", variant: "destructive" },
};

export function StatusBadge({ status }: { status: MemoryStatus }) {
  const config = statusConfig[status] ?? { label: status, variant: "outline" as const };
  return <Badge variant={config.variant}>{config.label}</Badge>;
}

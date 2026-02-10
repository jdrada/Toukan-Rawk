import { Badge } from "@/components/ui/badge";
import { MemoryStatus } from "@/types/memory";

const statusConfig: Record<
  MemoryStatus,
  { label: string; variant: "default" | "secondary" | "destructive" | "outline"; className?: string }
> = {
  [MemoryStatus.READY]: {
    label: "Ready",
    variant: "default",
    className: "bg-linear-to-r from-[var(--orange-gradient-from)] to-[var(--orange-gradient-to)] text-white border-0",
  },
  [MemoryStatus.PROCESSING]: {
    label: "Processing",
    variant: "secondary",
    className: "bg-linear-to-r from-[var(--orange-gradient-from)]/20 to-[var(--orange-gradient-to)]/20 text-[var(--orange-500)] border-[var(--orange-500)]/30",
  },
  [MemoryStatus.UPLOADING]: {
    label: "Uploading",
    variant: "outline",
    className: "border-[var(--orange-500)]/50 text-[var(--orange-500)]",
  },
  [MemoryStatus.FAILED]: { label: "Failed", variant: "destructive" },
};

export function StatusBadge({ status }: { status: MemoryStatus }) {
  const config = statusConfig[status] ?? { label: status, variant: "outline" as const };
  return (
    <Badge variant={config.variant} className={config.className}>
      {config.label}
    </Badge>
  );
}

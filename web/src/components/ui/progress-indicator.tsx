import { MemoryStatus } from "@/types/memory";

interface ProgressIndicatorProps {
  status: MemoryStatus;
}

export function ProgressIndicator({ status }: ProgressIndicatorProps) {
  if (status === MemoryStatus.READY || status === MemoryStatus.FAILED) {
    return null;
  }

  const steps = [
    { id: "uploading", label: "Uploading" },
    { id: "processing", label: "Processing" },
    { id: "ready", label: "Ready" },
  ];

  const currentStepIndex =
    status === MemoryStatus.UPLOADING ? 0 : status === MemoryStatus.PROCESSING ? 1 : 2;

  return (
    <div className="w-full space-y-2">
      <div className="flex items-center justify-between text-xs text-muted-foreground">
        {steps.map((step, index) => (
          <span
            key={step.id}
            className={
              index <= currentStepIndex
                ? "font-medium text-foreground"
                : ""
            }
          >
            {step.label}
          </span>
        ))}
      </div>
      <div className="relative h-1.5 w-full overflow-hidden rounded-full bg-muted">
        <div
          className="h-full bg-linear-to-r from-[var(--orange-gradient-from)] to-[var(--orange-gradient-to)] transition-all duration-500 ease-out"
          style={{
            width: `${((currentStepIndex + 1) / steps.length) * 100}%`,
          }}
        >
          {status === MemoryStatus.PROCESSING && (
            <div className="absolute inset-0 bg-linear-to-r from-transparent via-white/30 to-transparent animate-[shimmer_2s_infinite]" />
          )}
        </div>
      </div>
    </div>
  );
}

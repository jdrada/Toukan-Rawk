import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function MemoryNotFound() {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center max-w-3xl mx-auto">
      <h2 className="text-2xl font-bold">Memory not found</h2>
      <p className="mt-2 text-sm text-muted-foreground">
        This memory doesn&apos;t exist or may have been deleted.
      </p>
      <Button variant="outline" asChild className="mt-4">
        <Link href="/memories">Back to memories</Link>
      </Button>
    </div>
  );
}

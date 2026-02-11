import Link from "next/link";
import { ArrowRight, Mic, Brain, Search } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function HomePage() {
  return (
    <div className="flex flex-col items-center justify-center py-20 text-center">
      <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
        Your meetings,
        <br />
        <span className="text-primary">remembered.</span>
      </h1>
      <p className="mt-4 max-w-lg text-lg text-muted-foreground">
        Memories records your meetings, transcribes them with AI, and extracts
        summaries, key points, and action items so nothing gets lost.
      </p>
      <div className="mt-8">
        <Button asChild size="lg">
          <Link href="/memories">
            View your memories
            <ArrowRight className="ml-2 h-4 w-4" />
          </Link>
        </Button>
      </div>

      <div className="mt-20 grid gap-8 sm:grid-cols-3 max-w-2xl w-full">
        <Feature
          icon={<Mic className="h-6 w-6" />}
          title="Record"
          description="Speak to start recording. No buttons, no distractions."
        />
        <Feature
          icon={<Brain className="h-6 w-6" />}
          title="Understand"
          description="AI transcribes and summarizes your meetings automatically."
        />
        <Feature
          icon={<Search className="h-6 w-6" />}
          title="Review"
          description="Search and browse your memories with key points and action items."
        />
      </div>
    </div>
  );
}

function Feature({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="flex flex-col items-center gap-2">
      <div className="rounded-full bg-muted p-3">{icon}</div>
      <h3 className="font-semibold">{title}</h3>
      <p className="text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

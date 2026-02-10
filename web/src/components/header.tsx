import Link from "next/link";
import { ThemeToggle } from "@/components/theme-toggle";

export function Header() {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-14 items-center px-4">
        <Link href="/" className="mr-6 flex items-center space-x-2">
          <span className="text-xl font-bold tracking-tight bg-linear-to-r from-[#ff6b35] to-[#f7931e] bg-clip-text text-transparent">Toukan</span>
        </Link>
        <nav className="flex flex-1 items-center space-x-4 text-sm font-medium">
          <Link
            href="/memories"
            className="text-muted-foreground transition-colors hover:text-foreground"
          >
            Memories
          </Link>
        </nav>
        <ThemeToggle />
      </div>
    </header>
  );
}

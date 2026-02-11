import { MemoryDetailClient } from "@/components/memories/memory-detail-client";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function MemoryPage({ params }: Props) {
  const { id } = await params;
  return <MemoryDetailClient id={id} />;
}

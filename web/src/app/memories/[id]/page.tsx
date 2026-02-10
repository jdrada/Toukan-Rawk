import { notFound } from "next/navigation";
import { getMemory } from "@/lib/api";
import { MemoryDetail } from "@/components/memories/memory-detail";
import { ApiError } from "@/lib/api";

interface Props {
  params: Promise<{ id: string }>;
}

export default async function MemoryPage({ params }: Props) {
  const { id } = await params;

  let memory;
  try {
    memory = await getMemory(id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      notFound();
    }
    throw error;
  }

  return <MemoryDetail memory={memory} />;
}

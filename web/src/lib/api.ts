import { MemoryListResponse, MemoryResponse } from "@/types/memory";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "/api";

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function fetchApi<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || res.statusText);
  }

  const text = await res.text();
  return (text ? JSON.parse(text) : undefined) as T;
}

export async function getMemories(params?: {
  page?: number;
  page_size?: number;
  search?: string;
  status?: string;
}): Promise<MemoryListResponse> {
  const searchParams = new URLSearchParams();
  if (params?.page) searchParams.set("page", String(params.page));
  if (params?.page_size) searchParams.set("page_size", String(params.page_size));
  if (params?.search) searchParams.set("search", params.search);
  if (params?.status) searchParams.set("status", params.status);

  const query = searchParams.toString();
  return fetchApi<MemoryListResponse>(`/memories${query ? `?${query}` : ""}`);
}

export async function getMemory(id: string): Promise<MemoryResponse> {
  return fetchApi<MemoryResponse>(`/memories/${id}`);
}

export async function retryMemoryProcessing(id: string): Promise<MemoryResponse> {
  return fetchApi<MemoryResponse>(`/process/${id}`, {
    method: "POST",
  });
}

export async function deleteMemory(id: string): Promise<void> {
  await fetchApi<void>(`/memories/${id}`, {
    method: "DELETE",
  });
}

export { ApiError };

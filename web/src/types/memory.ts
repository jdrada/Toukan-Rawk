export enum MemoryStatus {
  UPLOADING = "uploading",
  PROCESSING = "processing",
  READY = "ready",
  FAILED = "failed",
}

export interface MemoryResponse {
  id: string;
  title: string | null;
  audio_url: string;
  status: MemoryStatus;
  transcript: string | null;
  summary: string | null;
  key_points: string[] | null;
  action_items: string[] | null;
  duration: number | null;
  created_at: string;
  updated_at: string;
}

export interface MemoryListResponse {
  items: MemoryResponse[];
  total: number;
  page: number;
  page_size: number;
  has_next: boolean;
}

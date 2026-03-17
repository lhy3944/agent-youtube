export interface SourceProgress {
  step: string | null;
  percent: number | null;
}

export interface Source {
  id: string;
  type: string;
  status: "pending" | "processing" | "ready" | "failed" | "partial_ready";
  original_url: string;
  external_id: string;
  title: string | null;
  channel_title: string | null;
  thumbnail_url: string | null;
  duration_sec: number | null;
  language: string | null;
  transcript_source: string | null;
  summary: string | null;
  error_message: string | null;
  progress: SourceProgress | null;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  segment_id: string;
  start_sec: number;
  end_sec: number;
  text: string;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
}

export interface ChatAskResponse {
  answer: string;
  session_id: string;
  citations: Citation[];
}

export interface SourceCreateResponse {
  source_id: string;
  status: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(error.detail || "API error");
  }
  return res.json();
}

export async function createYouTubeSource(url: string) {
  return apiFetch<{ source_id: string; status: string }>("/api/v1/sources/youtube", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

export async function getSource(sourceId: string) {
  return apiFetch<import("@/types").Source>(`/api/v1/sources/${sourceId}`);
}

export async function askQuestion(sourceId: string, question: string, sessionId?: string) {
  return apiFetch<import("@/types").ChatAskResponse>("/api/v1/chat/ask", {
    method: "POST",
    body: JSON.stringify({
      source_id: sourceId,
      session_id: sessionId || null,
      question,
    }),
  });
}

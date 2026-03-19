/**
 * 백엔드 API 클라이언트 모듈.
 *
 * 모든 API 호출은 이 모듈의 함수를 통해 이루어진다.
 * 기본 URL은 환경변수 NEXT_PUBLIC_API_URL로 설정하며,
 * 미설정 시 localhost:8000을 사용한다.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * 공통 API 호출 함수. 응답이 성공이 아닌 경우 에러를 throw한다.
 * 모든 요청에 Content-Type: application/json 헤더를 자동 추가한다.
 */
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

/** YouTube URL을 소스로 등록한다. 성공 시 source_id와 status를 반환한다. */
export async function createYouTubeSource(url: string) {
  return apiFetch<{ source_id: string; status: string }>("/api/v1/sources/youtube", {
    method: "POST",
    body: JSON.stringify({ url }),
  });
}

/** 소스의 상태, 메타데이터, 진행률을 조회한다. */
export async function getSource(sourceId: string) {
  return apiFetch<import("@/types").Source>(`/api/v1/sources/${sourceId}`);
}

/** 소스를 대상으로 질문하고 답변(Citation 포함)을 받는다. */
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

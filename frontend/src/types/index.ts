/** Ingest 파이프라인 진행 상황 */
export interface SourceProgress {
  step: string | null; // 현재 처리 단계 (metadata, captions, chunk, embed 등)
  percent: number | null; // 진행률 (0~100)
}

/** 등록된 영상 소스의 전체 정보 */
export interface Source {
  id: string;
  type: string; // 소스 유형 (현재 "youtube"만 지원)
  status: "pending" | "processing" | "ready" | "failed" | "partial_ready"; // 처리 상태
  original_url: string; // 사용자가 입력한 원본 YouTube URL
  external_id: string; // YouTube videoId (11자리)
  title: string | null; // 영상 제목
  channel_title: string | null; // 채널명
  thumbnail_url: string | null; // 썸네일 이미지 URL
  duration_sec: number | null; // 영상 길이(초)
  language: string | null; // 자막 언어 코드
  transcript_source: string | null; // 자막 출처: "caption" 또는 "stt"
  summary: string | null; // LLM이 생성한 영상 요약
  error_message: string | null; // 처리 실패 시 에러 메시지
  progress: SourceProgress | null; // processing 상태일 때 진행 상황
  created_at: string;
  updated_at: string;
}

/** 답변의 근거 구간 정보 (타임스탬프 + 원문 텍스트) */
export interface Citation {
  segment_id: string;
  start_sec: number; // 근거 구간 시작 시간(초)
  end_sec: number; // 근거 구간 종료 시간(초)
  text: string; // 해당 구간의 자막 텍스트
}

/** 채팅 메시지 (사용자 질문 또는 AI 답변) */
export interface ChatMessage {
  role: "user" | "assistant";
  content: string; // 메시지 본문
  citations?: Citation[]; // assistant 메시지에만 포함되는 근거 목록
}

/** POST /chat/ask 응답 */
export interface ChatAskResponse {
  answer: string; // AI 답변 텍스트
  session_id: string; // 세션 ID (다음 질문 시 전달하면 대화 이어감)
  citations: Citation[]; // 답변 근거 목록
}

/** POST /sources/youtube 응답 */
export interface SourceCreateResponse {
  source_id: string; // 생성된 소스 ID
  status: string; // 초기 상태 ("pending")
}

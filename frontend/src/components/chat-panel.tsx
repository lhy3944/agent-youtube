"use client";

/**
 * 채팅 패널 컴포넌트.
 *
 * 영상에 대한 질문/답변 대화 UI를 제공한다.
 *
 * 주요 기능:
 * - 사용자 질문 입력 및 전송
 * - AI 답변 + Citation(근거 타임스탬프) 표시
 * - 세션 기반 대화 히스토리 유지
 * - 답변 대기 중 로딩 애니메이션 표시
 * - 새 메시지 추가 시 자동 스크롤
 *
 * Citation 클릭 시 해당 타임스탬프의 YouTube 영상 페이지가 새 탭에서 열린다.
 */

import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { askQuestion } from "@/lib/api";
import { formatTimecode, youtubeTimestampUrl } from "@/lib/utils";
import type { ChatMessage, Citation } from "@/types";

/**
 * Citation 링크 컴포넌트.
 * 답변의 근거 구간을 타임코드로 표시하며, 클릭 시 YouTube 해당 시점으로 이동한다.
 */
function CitationLink({ citation, videoId }: { citation: Citation; videoId: string }) {
  const url = youtubeTimestampUrl(videoId, citation.start_sec);
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-secondary rounded-md hover:bg-accent transition-colors"
      title={citation.text} // 호버 시 해당 구간의 원문 텍스트 표시
    >
      <span className="font-mono">
        {formatTimecode(citation.start_sec)} - {formatTimecode(citation.end_sec)}
      </span>
    </a>
  );
}

export function ChatPanel({ sourceId, videoId }: { sourceId: string; videoId: string }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null); // 세션 ID: 첫 응답에서 받아 이후 질문에 전달
  const messagesEndRef = useRef<HTMLDivElement>(null); // 자동 스크롤용 ref

  const mutation = useMutation({
    mutationFn: (question: string) => askQuestion(sourceId, question, sessionId || undefined),
    onSuccess: (data) => {
      // 첫 응답에서 받은 session_id를 저장하여 이후 대화에서 맥락 유지
      setSessionId(data.session_id);
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer, citations: data.citations },
      ]);
    },
    onError: (error) => {
      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: `오류가 발생했습니다: ${error.message}` },
      ]);
    },
  });

  // 새 메시지 추가 시 채팅 영역 하단으로 자동 스크롤
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || mutation.isPending) return;
    const question = input.trim();
    setInput("");
    // 사용자 메시지를 즉시 UI에 추가 (낙관적 업데이트)
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    mutation.mutate(question);
  };

  return (
    <div className="space-y-4">
      {/* 메시지 목록 영역 */}
      <div className="space-y-4 max-h-[500px] overflow-y-auto">
        {messages.length === 0 && (
          <p className="text-sm text-muted-foreground text-center py-8">
            영상에 대해 궁금한 것을 물어보세요.
          </p>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
          >
            <div
              className={`max-w-[80%] rounded-xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-primary text-primary-foreground" // 사용자 메시지: 오른쪽 정렬, 주 색상
                  : "bg-secondary text-secondary-foreground" // AI 답변: 왼쪽 정렬, 보조 색상
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
              {/* AI 답변에 Citation이 있으면 타임스탬프 링크 목록 표시 */}
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {msg.citations.map((c, j) => (
                    <CitationLink key={j} citation={c} videoId={videoId} />
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}
        {/* 답변 생성 대기 중 로딩 애니메이션 */}
        {mutation.isPending && (
          <div className="flex justify-start">
            <div className="bg-secondary rounded-xl px-4 py-3">
              <div className="flex gap-1">
                <span className="animate-bounce">·</span>
                <span className="animate-bounce" style={{ animationDelay: "0.1s" }}>·</span>
                <span className="animate-bounce" style={{ animationDelay: "0.2s" }}>·</span>
              </div>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      {/* 질문 입력 폼 */}
      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="질문을 입력하세요..."
          className="flex-1 px-4 py-2.5 rounded-lg border border-input bg-background text-sm focus:outline-none focus:ring-2 focus:ring-ring"
          disabled={mutation.isPending}
        />
        <button
          type="submit"
          disabled={mutation.isPending || !input.trim()}
          className="px-5 py-2.5 bg-primary text-primary-foreground rounded-lg text-sm font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
        >
          전송
        </button>
      </form>
    </div>
  );
}

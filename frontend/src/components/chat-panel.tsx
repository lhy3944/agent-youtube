"use client";

import { useState, useRef, useEffect } from "react";
import { useMutation } from "@tanstack/react-query";
import { askQuestion } from "@/lib/api";
import { formatTimecode, youtubeTimestampUrl } from "@/lib/utils";
import type { ChatMessage, Citation } from "@/types";

function CitationLink({ citation, videoId }: { citation: Citation; videoId: string }) {
  const url = youtubeTimestampUrl(videoId, citation.start_sec);
  return (
    <a
      href={url}
      target="_blank"
      rel="noopener noreferrer"
      className="inline-flex items-center gap-1 px-2 py-1 text-xs bg-secondary rounded-md hover:bg-accent transition-colors"
      title={citation.text}
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
  const [sessionId, setSessionId] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const mutation = useMutation({
    mutationFn: (question: string) => askQuestion(sourceId, question, sessionId || undefined),
    onSuccess: (data) => {
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

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || mutation.isPending) return;
    const question = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: question }]);
    mutation.mutate(question);
  };

  return (
    <div className="space-y-4">
      {/* Messages */}
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
                  ? "bg-primary text-primary-foreground"
                  : "bg-secondary text-secondary-foreground"
              }`}
            >
              <p className="text-sm whitespace-pre-wrap">{msg.content}</p>
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

      {/* Input */}
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

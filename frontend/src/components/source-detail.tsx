"use client";

import Image from "next/image";
import { useQuery } from "@tanstack/react-query";
import { getSource } from "@/lib/api";
import { formatDuration } from "@/lib/utils";
import { StatusBadge } from "./status-badge";
import { ChatPanel } from "./chat-panel";
import type { Source } from "@/types";

const STEP_LABELS: Record<string, string> = {
  queued: "대기 중",
  metadata: "메타데이터 수집",
  captions: "자막 확보",
  stt: "음성 인식",
  normalize: "텍스트 정규화",
  chunk: "청크 생성",
  embed: "임베딩 생성",
  summary: "요약 생성",
  done: "완료",
};

export function SourceDetail({ sourceId }: { sourceId: string }) {
  const { data: source, isLoading } = useQuery<Source>({
    queryKey: ["source", sourceId],
    queryFn: () => getSource(sourceId),
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      if (status === "pending" || status === "processing") return 2000;
      return false;
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary" />
      </div>
    );
  }

  if (!source) {
    return <div className="text-center py-12 text-muted-foreground">소스를 찾을 수 없습니다.</div>;
  }

  const isReady = source.status === "ready" || source.status === "partial_ready";

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header Card */}
      <div className="bg-card rounded-xl border p-6">
        <div className="flex gap-6">
          {source.thumbnail_url && (
            <div className="flex-shrink-0">
              <Image
                src={source.thumbnail_url}
                alt={source.title || "Video thumbnail"}
                width={320}
                height={180}
                className="rounded-lg object-cover"
              />
            </div>
          )}
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <StatusBadge status={source.status} />
              {source.transcript_source && (
                <span className="text-xs text-muted-foreground">
                  ({source.transcript_source})
                </span>
              )}
            </div>
            <h1 className="text-xl font-bold">{source.title || "제목 로딩 중..."}</h1>
            {source.channel_title && (
              <p className="text-sm text-muted-foreground">{source.channel_title}</p>
            )}
            {source.duration_sec && (
              <p className="text-sm text-muted-foreground">
                길이: {formatDuration(source.duration_sec)}
              </p>
            )}
          </div>
        </div>

        {/* Progress */}
        {source.progress && source.status === "processing" && (
          <div className="mt-4 space-y-2">
            <div className="flex justify-between text-sm text-muted-foreground">
              <span>{STEP_LABELS[source.progress.step || ""] || source.progress.step}</span>
              <span>{source.progress.percent}%</span>
            </div>
            <div className="w-full bg-secondary rounded-full h-2">
              <div
                className="bg-primary h-2 rounded-full transition-all duration-500"
                style={{ width: `${source.progress.percent || 0}%` }}
              />
            </div>
          </div>
        )}

        {/* Error */}
        {source.status === "failed" && source.error_message && (
          <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
            {source.error_message}
          </div>
        )}
      </div>

      {/* Summary */}
      {source.summary && (
        <div className="bg-card rounded-xl border p-6">
          <h2 className="text-lg font-semibold mb-3">요약</h2>
          <p className="text-sm leading-relaxed whitespace-pre-wrap">{source.summary}</p>
        </div>
      )}

      {/* Chat */}
      <div className="bg-card rounded-xl border p-6">
        <h2 className="text-lg font-semibold mb-4">질문하기</h2>
        {isReady ? (
          <ChatPanel sourceId={sourceId} videoId={source.external_id} />
        ) : (
          <p className="text-sm text-muted-foreground">
            {source.status === "failed"
              ? "처리에 실패하여 질문할 수 없습니다."
              : "영상 처리가 완료되면 질문할 수 있습니다."}
          </p>
        )}
      </div>
    </div>
  );
}

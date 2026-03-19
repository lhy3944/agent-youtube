"use client";

/**
 * YouTube URL 입력 폼 컴포넌트.
 *
 * 사용자가 YouTube URL을 입력하고 등록 버튼을 클릭하면:
 * 1. createYouTubeSource API를 호출하여 소스를 등록한다
 * 2. 성공 시 소스 상세 페이지(/source/{id})로 자동 이동한다
 *
 * useMutation으로 API 호출 상태(로딩, 에러)를 관리한다.
 */

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useMutation } from "@tanstack/react-query";
import { createYouTubeSource } from "@/lib/api";

export function UrlInputForm() {
  const [url, setUrl] = useState("");
  const router = useRouter();

  const mutation = useMutation({
    mutationFn: (url: string) => createYouTubeSource(url),
    onSuccess: (data) => {
      // 소스 등록 성공 → 상세 페이지로 이동
      router.push(`/source/${data.source_id}`);
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;
    mutation.mutate(url.trim());
  };

  return (
    <form onSubmit={handleSubmit} className="flex gap-3 w-full max-w-2xl">
      <input
        type="url"
        value={url}
        onChange={(e) => setUrl(e.target.value)}
        placeholder="YouTube URL을 입력하세요..."
        className="flex-1 px-4 py-3 rounded-lg border border-input bg-background text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-ring"
        disabled={mutation.isPending}
      />
      <button
        type="submit"
        disabled={mutation.isPending || !url.trim()}
        className="px-6 py-3 bg-primary text-primary-foreground rounded-lg font-medium hover:opacity-90 disabled:opacity-50 disabled:cursor-not-allowed transition-opacity"
      >
        {mutation.isPending ? "등록 중..." : "등록"}
      </button>
    </form>
  );
}

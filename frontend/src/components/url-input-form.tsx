"use client";

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

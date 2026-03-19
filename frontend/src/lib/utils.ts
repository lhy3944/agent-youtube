/**
 * 공통 유틸리티 함수 모듈.
 *
 * - cn(): Tailwind CSS 클래스명 병합 유틸리티
 * - formatTimecode(): 초 → 타임코드 변환
 * - youtubeTimestampUrl(): YouTube 특정 시점 URL 생성
 */

import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

/** Tailwind CSS 클래스명을 조건부로 병합한다. clsx + tailwind-merge 조합. */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** 초 단위 시간을 사람이 읽기 쉬운 타임코드(M:SS 또는 H:MM:SS)로 변환한다. */
export function formatTimecode(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
  }
  return `${m}:${s.toString().padStart(2, "0")}`;
}

/** 초 단위 영상 길이를 포맷팅한다. (formatTimecode와 동일 형식) */
export function formatDuration(seconds: number): string {
  return formatTimecode(seconds);
}

/** YouTube 영상의 특정 시점으로 이동하는 URL을 생성한다.
 * Citation 클릭 시 해당 타임스탬프의 YouTube 페이지를 새 탭에서 연다. */
export function youtubeTimestampUrl(videoId: string, startSec: number): string {
  return `https://www.youtube.com/watch?v=${videoId}&t=${Math.floor(startSec)}s`;
}

"use client";

/**
 * React Query Provider 컴포넌트.
 *
 * 앱 전체에서 서버 상태 관리(데이터 fetching, 캐싱, 동기화)를 위해
 * TanStack React Query의 QueryClient를 제공한다.
 *
 * - staleTime: 5초 (5초 이내 동일 쿼리 재요청 방지)
 * - retry: 1회 (실패 시 1번만 재시도)
 */

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { useState } from "react";

export function Providers({ children }: { children: React.ReactNode }) {
  // useState 내부에서 생성하여 서버/클라이언트 간 QueryClient 공유 방지
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            staleTime: 5000,
            retry: 1,
          },
        },
      })
  );

  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}

/**
 * 루트 레이아웃.
 *
 * 앱 전체의 HTML 구조, 폰트, 메타데이터를 설정하고,
 * React Query Provider로 모든 페이지를 감싼다.
 */

import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";
import { Providers } from "@/components/providers";

const inter = Inter({ subsets: ["latin"] });

export const metadata: Metadata = {
  title: "YouTube QA Agent",
  description: "Ask questions about any YouTube video",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className={inter.className}>
        <Providers>
          <main className="min-h-screen">{children}</main>
        </Providers>
      </body>
    </html>
  );
}

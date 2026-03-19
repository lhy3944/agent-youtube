/**
 * 소스 상세 페이지 (/source/[id]).
 *
 * 동적 라우트로 sourceId를 URL 파라미터에서 받아
 * SourceDetail 컴포넌트에 전달한다.
 *
 * Next.js App Router의 async params를 사용한다.
 */

import { SourceDetail } from "@/components/source-detail";

export default async function SourcePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="p-8">
      <SourceDetail sourceId={id} />
    </div>
  );
}

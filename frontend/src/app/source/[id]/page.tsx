import { SourceDetail } from "@/components/source-detail";

export default async function SourcePage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return (
    <div className="p-8">
      <SourceDetail sourceId={id} />
    </div>
  );
}

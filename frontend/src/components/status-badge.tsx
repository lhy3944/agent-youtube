import { cn } from "@/lib/utils";

const statusConfig: Record<string, { label: string; className: string }> = {
  pending: { label: "대기 중", className: "bg-yellow-100 text-yellow-800" },
  processing: { label: "처리 중", className: "bg-blue-100 text-blue-800" },
  ready: { label: "준비 완료", className: "bg-green-100 text-green-800" },
  partial_ready: { label: "부분 완료", className: "bg-green-100 text-green-700" },
  failed: { label: "실패", className: "bg-red-100 text-red-800" },
};

export function StatusBadge({ status }: { status: string }) {
  const config = statusConfig[status] || { label: status, className: "bg-gray-100 text-gray-800" };
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
        config.className
      )}
    >
      {config.label}
    </span>
  );
}

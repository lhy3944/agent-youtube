import { UrlInputForm } from "@/components/url-input-form";

export default function HomePage() {
  return (
    <div className="flex flex-col items-center justify-center min-h-screen p-8">
      <div className="text-center space-y-6 max-w-2xl">
        <h1 className="text-4xl font-bold tracking-tight">YouTube QA Agent</h1>
        <p className="text-lg text-muted-foreground">
          YouTube 영상 URL을 입력하면 영상 내용을 분석하고, 질문에 답변해 드립니다.
        </p>
        <UrlInputForm />
      </div>
    </div>
  );
}

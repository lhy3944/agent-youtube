# YouTube QA Agent - Frontend

YouTube 영상 Q&A 에이전트의 프론트엔드 애플리케이션입니다. 사용자가 YouTube URL을 등록하고, 영상 내용에 대해 질문하며, 타임스탬프 기반 근거와 함께 답변을 확인할 수 있습니다.

## 기술 스택

| 구성 요소 | 기술 |
|-----------|------|
| 프레임워크 | Next.js 14 (App Router) |
| 언어 | TypeScript |
| 서버 상태 관리 | TanStack React Query v5 |
| 스타일링 | Tailwind CSS |
| 아이콘 | Lucide React |
| 유틸리티 | clsx + tailwind-merge |

## 아키텍처 개요

```
┌─────────────────────────────────────────────────────────┐
│                    Next.js App Router                     │
│                                                          │
│  ┌─────────────┐    ┌────────────────────────────────┐  │
│  │ 메인 페이지  │    │      소스 상세 페이지            │  │
│  │  /          │    │  /source/[id]                   │  │
│  │             │    │                                 │  │
│  │ UrlInputForm│    │ SourceDetail                    │  │
│  │             │    │  ├── 메타데이터 카드 (썸네일 등)  │  │
│  └──────┬──────┘    │  ├── 처리 상태/진행률 표시       │  │
│         │           │  ├── 요약 카드                   │  │
│         │           │  └── ChatPanel                  │  │
│         │           │       ├── 메시지 목록            │  │
│         │           │       ├── CitationLink (근거)    │  │
│         │           │       └── 질문 입력창            │  │
│         │           └────────────────────────────────┘  │
│         │                                                │
│  ┌──────▼──────────────────────────────────────────────┐│
│  │               API 클라이언트 (lib/api.ts)            ││
│  │  createYouTubeSource │ getSource │ askQuestion       ││
│  └──────────────────────┬───────────────────────────────┘│
└─────────────────────────┼────────────────────────────────┘
                          │
                          ▼
                  FastAPI 백엔드 (localhost:8000)
```

## 디렉토리 구조

```
frontend/src/
├── app/                        # Next.js App Router 페이지
│   ├── layout.tsx              # 루트 레이아웃 (Providers 래핑, 메타데이터)
│   ├── page.tsx                # 메인 페이지 (URL 입력 화면)
│   ├── globals.css             # 글로벌 스타일 (Tailwind base)
│   └── source/
│       └── [id]/
│           └── page.tsx        # 소스 상세 페이지 (동적 라우트)
├── components/                 # UI 컴포넌트
│   ├── providers.tsx           # React Query Provider 설정
│   ├── url-input-form.tsx      # YouTube URL 입력 폼 (등록 → 상세페이지 이동)
│   ├── source-detail.tsx       # 소스 상세: 메타데이터, 진행률, 요약, 채팅
│   ├── chat-panel.tsx          # 채팅 UI: 메시지 목록 + Citation 링크 + 입력창
│   └── status-badge.tsx        # 소스 처리 상태 배지 (pending/processing/ready 등)
├── lib/                        # 유틸리티 및 API 클라이언트
│   ├── api.ts                  # 백엔드 API 호출 함수
│   └── utils.ts                # 타임코드 포매팅, YouTube URL 생성, cn() 유틸
└── types/
    └── index.ts                # TypeScript 타입 정의 (Source, Citation, ChatMessage 등)
```

## 주요 화면

### 1. 메인 페이지 (`/`)
- YouTube URL 입력 필드 + 등록 버튼
- 등록 성공 시 소스 상세 페이지(`/source/{id}`)로 자동 이동

### 2. 소스 상세 페이지 (`/source/[id]`)
- **메타데이터 카드**: 썸네일, 제목, 채널명, 영상 길이, 상태 배지
- **진행률 표시**: `processing` 상태일 때 현재 단계 + 퍼센트 프로그레스 바 (2초 간격 자동 polling)
- **요약 카드**: 영상 전체 요약 (ready 상태에서 표시)
- **채팅 패널**: 질문/답변 메시지 목록 + Citation 타임스탬프 링크

## 핵심 데이터 흐름

```
1. 사용자 URL 입력
   └─→ useMutation(createYouTubeSource)
       └─→ 성공 시 router.push(/source/{id})

2. 소스 상세 페이지 진입
   └─→ useQuery(getSource, { refetchInterval: 2000 })  ← pending/processing일 때만 polling
       └─→ 상태별 UI 렌더링

3. 사용자 질문 입력
   └─→ useMutation(askQuestion)
       └─→ 응답의 answer + citations를 메시지 목록에 추가
           └─→ Citation 클릭 → YouTube 타임스탬프 URL 열기
```

## 주요 컴포넌트 설명

| 컴포넌트 | 역할 |
|----------|------|
| `Providers` | React Query의 QueryClient를 앱 전체에 제공 |
| `UrlInputForm` | URL 입력, 유효성 확인, 소스 등록 API 호출 |
| `SourceDetail` | 소스 메타데이터/상태/요약 표시, 처리 중 자동 polling |
| `ChatPanel` | 채팅 메시지 관리, 세션 유지, 질문 전송 |
| `CitationLink` | Citation을 YouTube 타임스탬프 링크로 렌더링 |
| `StatusBadge` | 소스 상태를 색상 배지로 표시 |

## 개발 환경 설정

```bash
# 1. 의존성 설치
npm install

# 2. 환경변수 설정 (백엔드 API 주소)
# 기본값: http://localhost:8000
# 필요 시 .env.local 파일에 NEXT_PUBLIC_API_URL 설정

# 3. 개발 서버 실행
npm run dev
# → http://localhost:3000
```

## 설정 항목

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `NEXT_PUBLIC_API_URL` | 백엔드 API 서버 주소 | `http://localhost:8000` |

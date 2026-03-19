"""
FastAPI 애플리케이션 진입점.

CORS 미들웨어를 설정하고, API 라우터(sources, chat)를 /api/v1 프리픽스로 등록한다.
프론트엔드(localhost:3000)에서의 교차 출처 요청을 허용한다.

Swagger UI: http://localhost:8000/docs
ReDoc:      http://localhost:8000/redoc
OpenAPI JSON: http://localhost:8000/openapi.json
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.chat import router as chat_router
from app.api.v1.sources import router as sources_router

# Swagger UI에 표시되는 API 문서 메타데이터
app = FastAPI(
    title="YouTube QA Agent API",
    version="0.1.0",
    summary="YouTube 영상 URL을 기반으로 영상 내용을 분석하고 질문에 답변하는 에이전트 API",
    description="""
## 개요

YouTube 영상 URL을 소스로 등록하면, 영상의 자막을 자동으로 수집·분석하여
자연어 질문에 타임스탬프 근거(Citation)와 함께 답변합니다.

## 주요 흐름

1. **소스 등록** — `POST /api/v1/sources/youtube`로 YouTube URL 등록
2. **상태 확인** — `GET /api/v1/sources/{sourceId}`로 처리 진행률 polling
3. **질문하기** — `POST /api/v1/chat/ask`로 영상 내용에 대해 질문

## 상태(Status) 설명

| 상태 | 설명 |
|------|------|
| `pending` | 소스 등록됨, 처리 대기 |
| `processing` | Ingest 파이프라인 실행 중 |
| `ready` | 모든 처리 완료, 질문 가능 |
| `partial_ready` | 요약 생성 실패했으나 질문은 가능 |
| `failed` | 처리 실패 |

## Ingest 파이프라인 단계

`metadata` → `captions` → `normalize` → `chunk` → `embed` → `summary` → `done`
""",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "sources",
            "description": "YouTube 영상 소스 등록 및 조회. URL 등록, 상태 확인, 세그먼트 조회 등.",
        },
        {
            "name": "chat",
            "description": "영상 기반 질문/답변. 등록된 소스에 대해 자연어 질문을 하고 Citation이 포함된 답변을 받는다.",
        },
        {
            "name": "system",
            "description": "시스템 상태 확인용 엔드포인트.",
        },
    ],
)

# 프론트엔드 개발 서버에서의 CORS 요청 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API v1 라우터 등록
app.include_router(sources_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health_check():
    """서버 상태 확인용 헬스 체크 엔드포인트."""
    return {"status": "ok"}

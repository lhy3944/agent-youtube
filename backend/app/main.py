"""
FastAPI 애플리케이션 진입점.

CORS 미들웨어를 설정하고, API 라우터(sources, chat)를 /api/v1 프리픽스로 등록한다.
프론트엔드에서의 교차 출처 요청을 허용한다.

Swagger UI: /docs
ReDoc:      /redoc
OpenAPI JSON: /openapi.json
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.chat import router as chat_router
from app.api.v1.sources import router as sources_router
from app.core.database import Base, engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """앱 시작 시 pgvector 확장을 활성화하고 DB 테이블을 자동 생성한다."""
    # 모든 모델을 import하여 Base.metadata에 등록
    import app.models.chat  # noqa: F401
    import app.models.ingest_job  # noqa: F401
    import app.models.source  # noqa: F401
    import app.models.transcript_segment  # noqa: F401

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully")
    yield

# 허용할 프론트엔드 Origin 목록
ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "https://agent.devbanjang.cloud",
]

# Swagger UI에 표시되는 API 문서 메타데이터
app = FastAPI(
    title="YouTube QA Agent API",
    version="0.1.0",
    lifespan=lifespan,
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

# 프론트엔드에서의 CORS 요청 허용 (개발 환경 + 프로덕션 환경)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """처리되지 않은 예외를 잡아 CORS 헤더가 포함된 500 응답을 반환한다.

    FastAPI의 CORSMiddleware는 정상 응답에만 CORS 헤더를 추가하므로,
    unhandled exception이 발생하면 브라우저에서 CORS 오류로 표시될 수 있다.
    이 핸들러가 그 문제를 방지한다.
    """
    logger.exception(f"Unhandled error on {request.method} {request.url}: {exc}")

    origin = request.headers.get("origin", "")
    headers = {}
    if origin in ALLOWED_ORIGINS:
        headers["access-control-allow-origin"] = origin
        headers["access-control-allow-credentials"] = "true"

    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {type(exc).__name__}: {str(exc)}"},
        headers=headers,
    )


# API v1 라우터 등록
app.include_router(sources_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")


@app.get("/health", tags=["system"])
async def health_check():
    """서버 상태 확인용 헬스 체크 엔드포인트."""
    return {"status": "ok"}

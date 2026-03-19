"""
FastAPI 애플리케이션 진입점.

CORS 미들웨어를 설정하고, API 라우터(sources, chat)를 /api/v1 프리픽스로 등록한다.
프론트엔드(localhost:3000)에서의 교차 출처 요청을 허용한다.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.chat import router as chat_router
from app.api.v1.sources import router as sources_router

app = FastAPI(title="YouTube QA Agent", version="0.1.0")

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


@app.get("/health")
async def health_check():
    """서버 상태 확인용 헬스 체크 엔드포인트."""
    return {"status": "ok"}

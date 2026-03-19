"""
Chat API 라우터.

엔드포인트:
- POST /chat/ask : 등록된 소스(영상)에 대해 질문하고 답변을 받는다

질문 처리 흐름:
  1. 소스 상태 검증 (ready 또는 partial_ready만 질문 가능)
  2. 세션 조회/생성 (세션 ID가 있으면 기존 세션 이어가기)
  3. 이전 대화 히스토리 로드 (맥락 유지)
  4. 벡터 검색으로 관련 세그먼트 조회
  5. LLM으로 답변 생성 (Citation 포함)
  6. 메시지(user/assistant) DB에 저장
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.chat import ChatMessage, ChatSession
from app.models.source import Source
from app.schemas.chat import ChatAskRequest, ChatAskResponse, Citation
from app.services.answer import generate_answer
from app.services.retrieval import retrieve_relevant_segments

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask", response_model=ChatAskResponse)
async def ask_question(
    body: ChatAskRequest,
    db: AsyncSession = Depends(get_db),
):
    """영상 내용을 기반으로 질문에 답변한다.

    - 소스가 ready/partial_ready 상태가 아니면 질문 불가
    - session_id가 없으면 새 세션 생성, 있으면 기존 세션의 대화 이어가기
    - 답변에는 반드시 Citation(근거 타임스탬프 구간)이 포함된다
    """
    # 소스 존재 여부 및 상태 검증
    source = await db.get(Source, body.source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.status not in ("ready", "partial_ready"):
        raise HTTPException(
            status_code=400,
            detail=f"Source is not ready for questions. Current status: {source.status}",
        )

    # 세션 조회 또는 신규 생성
    if body.session_id:
        session = await db.get(ChatSession, body.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        # 첫 질문 시 새 세션 자동 생성
        session = ChatSession(source_id=source.id)
        db.add(session)
        await db.flush()

    # 기존 세션이면 이전 대화 히스토리 로드 (LLM에 맥락 전달용)
    chat_history = []
    if body.session_id:
        stmt = (
            select(ChatMessage)
            .where(ChatMessage.session_id == session.id)
            .order_by(ChatMessage.created_at)
        )
        result = await db.execute(stmt)
        for msg in result.scalars().all():
            chat_history.append({"role": msg.role, "content": msg.content})

    # 질문과 관련된 자막 세그먼트를 벡터 유사도 검색으로 조회
    segments = await retrieve_relevant_segments(db, source.id, body.question)

    # 검색된 세그먼트를 근거로 LLM이 답변 생성
    answer_data = await generate_answer(body.question, segments, chat_history)

    # 사용자 질문과 AI 답변을 DB에 저장 (대화 히스토리 유지)
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=body.question,
    )
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer_data["answer"],
        citations=answer_data["citations"],  # Citation 정보를 JSON으로 저장
    )
    db.add(user_msg)
    db.add(assistant_msg)
    await db.commit()

    citations = [Citation(**c) for c in answer_data["citations"]]

    return ChatAskResponse(
        answer=answer_data["answer"],
        session_id=session.id,
        citations=citations,
    )

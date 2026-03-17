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
    # Validate source
    source = await db.get(Source, body.source_id)
    if not source:
        raise HTTPException(status_code=404, detail="Source not found")
    if source.status not in ("ready", "partial_ready"):
        raise HTTPException(
            status_code=400,
            detail=f"Source is not ready for questions. Current status: {source.status}",
        )

    # Get or create session
    if body.session_id:
        session = await db.get(ChatSession, body.session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
    else:
        session = ChatSession(source_id=source.id)
        db.add(session)
        await db.flush()

    # Load chat history
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

    # Retrieve relevant segments
    segments = await retrieve_relevant_segments(db, source.id, body.question)

    # Generate answer
    answer_data = await generate_answer(body.question, segments, chat_history)

    # Save messages
    user_msg = ChatMessage(
        session_id=session.id,
        role="user",
        content=body.question,
    )
    assistant_msg = ChatMessage(
        session_id=session.id,
        role="assistant",
        content=answer_data["answer"],
        citations=answer_data["citations"],
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

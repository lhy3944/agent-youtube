"""
Ingest 파이프라인 Celery 태스크.

YouTube 소스 등록 후 비동기로 실행되는 전체 처리 파이프라인이다.

파이프라인 단계:
  ① metadata  - 영상 메타데이터 조회 (제목, 채널명, 썸네일 등)
  ② captions  - 자막 확보 (youtube-transcript-api)
  ③ stt       - 자막 실패 시 STT fallback (현재 미구현)
  ④ normalize - 자막 텍스트 정규화 (노이즈 제거, 타임스탬프 정리)
  ⑤ chunk     - 토큰 기반 청크 분할 (오버랩 포함)
  ⑥ embed     - OpenAI 임베딩 벡터 생성 + DB 저장
  ⑦ summary   - LLM 기반 영상 요약 생성

각 단계에서 IngestJob의 step/progress를 업데이트하여
프론트엔드에서 실시간 진행 상황을 polling할 수 있도록 한다.
"""

import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
# 모든 모델을 import하여 SQLAlchemy가 relationship을 해석할 수 있도록 한다
from app.models.chat import ChatMessage, ChatSession  # noqa: F401
from app.models.ingest_job import IngestJob
from app.models.source import Source
from app.models.transcript_segment import TranscriptSegment
from app.services.answer import generate_summary
from app.services.chunking import chunk_segments
from app.services.embedding import embed_texts
from app.services.transcript import fetch_captions, normalize_transcript
from app.services.youtube import fetch_video_metadata
from app.worker.celery_app import celery_app

logger = logging.getLogger(__name__)


def _get_async_session_factory():
    """Celery 워커 프로세스용 별도의 비동기 DB 세션 팩토리를 생성한다.
    (워커는 FastAPI와 다른 프로세스이므로 독립적인 엔진이 필요)"""
    engine = create_async_engine(settings.DATABASE_URL)
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _run_ingest(source_id: str, job_id: str):
    """Ingest 파이프라인의 실제 비동기 실행 로직.

    모든 단계를 순차적으로 실행하며, 각 단계 완료 시 DB에 진행 상황을 커밋한다.
    어떤 단계에서든 실패하면 source.status = "failed"로 설정되고 에러 메시지가 저장된다.
    """
    factory = _get_async_session_factory()

    async with factory() as db:
        source = await db.get(Source, uuid.UUID(source_id))
        job = await db.get(IngestJob, uuid.UUID(job_id))
        if not source or not job:
            logger.error(f"Source or job not found: {source_id}, {job_id}")
            return

        try:
            # ① 메타데이터 조회: 영상 제목, 채널명, 썸네일, 길이 등
            job.step = "metadata"
            job.progress = 10
            source.status = "processing"
            await db.commit()

            metadata = await fetch_video_metadata(source.external_id)
            if metadata:
                source.title = metadata.get("title")
                source.channel_title = metadata.get("channel_title")
                source.description = metadata.get("description")
                source.thumbnail_url = metadata.get("thumbnail_url")
                source.duration_sec = metadata.get("duration_sec")
                await db.commit()

            # ② 자막 확보: youtube-transcript-api를 통해 자막 데이터 가져오기
            job.step = "captions"
            job.progress = 20
            await db.commit()

            raw_segments = fetch_captions(source.external_id)
            if raw_segments is None:
                # ③ STT fallback: 자막이 없는 경우 음성 인식으로 전환 (현재 미구현)
                job.step = "stt"
                job.progress = 25
                await db.commit()
                raise ValueError("No captions available and STT not yet implemented")

            source.transcript_source = "caption"

            # ④ 텍스트 정규화: 노이즈 제거, 타임스탬프 정리
            job.step = "normalize"
            job.progress = 40
            await db.commit()

            normalized = normalize_transcript(raw_segments)
            if not normalized:
                raise ValueError("Transcript normalization produced no segments")

            # ⑤ 청크 분할: 토큰 기반으로 검색에 적합한 크기로 분할
            job.step = "chunk"
            job.progress = 50
            await db.commit()

            chunks = chunk_segments(normalized)

            # ⑥ 임베딩 생성: OpenAI API로 각 청크의 벡터 임베딩 생성
            job.step = "embed"
            job.progress = 60
            await db.commit()

            # 배치 단위로 임베딩 생성 (API 호출 최적화)
            texts = [c["text"] for c in chunks]
            batch_size = 50
            all_embeddings = []
            for i in range(0, len(texts), batch_size):
                batch = texts[i : i + batch_size]
                embeddings = await embed_texts(batch)
                all_embeddings.extend(embeddings)
                # 임베딩 진행률을 60%~80% 구간에서 업데이트
                job.progress = 60 + int(20 * (i + len(batch)) / len(texts))
                await db.commit()

            # 청크 + 임베딩을 TranscriptSegment 레코드로 저장
            for idx, (chunk, emb) in enumerate(zip(chunks, all_embeddings)):
                segment = TranscriptSegment(
                    source_id=source.id,
                    segment_index=idx,
                    start_sec=chunk["start_sec"],
                    end_sec=chunk["end_sec"],
                    text=chunk["text"],
                    token_count=chunk["token_count"],
                    embedding=emb,
                )
                db.add(segment)

            await db.commit()

            # ⑦ 요약 생성: 전체 자막을 LLM에 전달하여 요약 텍스트 생성
            job.step = "summary"
            job.progress = 85
            await db.commit()

            stmt = (
                select(TranscriptSegment)
                .where(TranscriptSegment.source_id == source.id)
                .order_by(TranscriptSegment.segment_index)
            )
            result = await db.execute(stmt)
            all_segments = list(result.scalars().all())

            summary = await generate_summary(all_segments)
            if summary:
                source.summary = summary

            # 처리 완료: 요약 성공 시 ready, 요약만 실패 시 partial_ready
            job.step = "done"
            job.progress = 100
            job.status = "completed"
            source.status = "ready" if summary else "partial_ready"
            await db.commit()

        except Exception as e:
            # 파이프라인 실패: 에러 로그 기록 및 상태 업데이트
            logger.exception(f"Ingest failed for source {source_id}: {e}")
            job.status = "failed"
            job.error_message = str(e)
            source.status = "failed"
            source.error_message = str(e)
            await db.commit()


@celery_app.task(name="ingest_youtube_source")
def ingest_youtube_source(source_id: str, job_id: str):
    """Celery 태스크 진입점. 비동기 파이프라인을 asyncio.run으로 실행한다."""
    asyncio.run(_run_ingest(source_id, job_id))

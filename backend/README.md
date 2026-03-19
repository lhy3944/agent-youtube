# YouTube QA Agent - Backend

YouTube 영상 URL을 기반으로 영상 내용을 분석하고 질문에 답변하는 에이전트의 백엔드 서비스입니다.

## 기술 스택

| 구성 요소 | 기술 |
|-----------|------|
| API 서버 | FastAPI (비동기) |
| ORM | SQLAlchemy 2.0 (async) |
| 데이터 검증 | Pydantic v2 |
| 비동기 작업 큐 | Celery + Redis |
| 데이터베이스 | PostgreSQL + pgvector (벡터 검색) |
| 임베딩/LLM | OpenAI API (text-embedding-3-small, gpt-4o-mini) |
| 자막 추출 | youtube-transcript-api |

## 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────┐
│                        FastAPI 서버                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │ Sources API  │  │  Chat API    │  │  Health Check    │   │
│  │ /sources/*   │  │  /chat/ask   │  │  /health         │   │
│  └──────┬───────┘  └──────┬───────┘  └──────────────────┘   │
│         │                 │                                  │
│  ┌──────▼─────────────────▼──────────────────────────────┐  │
│  │                   서비스 레이어                         │  │
│  │  youtube │ transcript │ chunking │ embedding │ answer  │  │
│  │          │            │          │ retrieval │         │  │
│  └──────────────────────────────────────────────────────┘   │
└─────────┬───────────────────────────────────────────────────┘
          │
    ┌─────▼──────┐     ┌────────────┐     ┌──────────────┐
    │ PostgreSQL │     │   Redis    │     │ Celery Worker│
    │ + pgvector │     │  (브로커)   │     │ (Ingest 처리)│
    └────────────┘     └────────────┘     └──────────────┘
```

## 디렉토리 구조

```
backend/
├── app/
│   ├── main.py                 # FastAPI 앱 진입점, 미들웨어 및 라우터 등록
│   ├── core/
│   │   ├── config.py           # 환경변수 기반 설정 (Pydantic Settings)
│   │   └── database.py         # 비동기 DB 엔진 및 세션 팩토리
│   ├── models/                 # SQLAlchemy ORM 모델
│   │   ├── source.py           # Source: 등록된 영상 소스 (상태, 메타데이터)
│   │   ├── transcript_segment.py # TranscriptSegment: 청크화된 자막 + 벡터 임베딩
│   │   ├── chat.py             # ChatSession / ChatMessage: 대화 세션 및 메시지
│   │   └── ingest_job.py       # IngestJob: 비동기 처리 작업 추적
│   ├── schemas/                # Pydantic 요청/응답 스키마
│   │   ├── source.py           # 소스 생성/조회 스키마
│   │   ├── chat.py             # 질문 요청/응답 및 Citation 스키마
│   │   └── segment.py          # 세그먼트 조회 스키마
│   ├── api/v1/                 # API 라우터 (버전별)
│   │   ├── sources.py          # POST /sources/youtube, GET /sources/{id}
│   │   └── chat.py             # POST /chat/ask
│   ├── services/               # 비즈니스 로직 서비스
│   │   ├── youtube.py          # URL 파싱, videoId 추출, 메타데이터 조회
│   │   ├── transcript.py       # 자막 확보 (youtube-transcript-api) + 정규화
│   │   ├── chunking.py         # 토큰 기반 청크 분할 (오버랩 포함)
│   │   ├── embedding.py        # OpenAI 임베딩 생성
│   │   ├── retrieval.py        # pgvector 코사인 유사도 검색
│   │   └── answer.py           # LLM 답변 생성 + 요약 생성
│   └── worker/                 # Celery 비동기 워커
│       ├── celery_app.py       # Celery 앱 설정
│       └── tasks.py            # Ingest 파이프라인 태스크
├── alembic/                    # DB 마이그레이션
│   ├── env.py
│   └── versions/
│       └── 001_initial.py      # 초기 스키마 (sources, segments, chat, jobs)
├── tests/                      # 테스트
├── pyproject.toml              # Python 패키지 설정 및 의존성
├── alembic.ini                 # Alembic 설정
├── Dockerfile
└── .env.example                # 환경변수 예시
```

## 핵심 데이터 흐름

### 1. 소스 등록 (Ingest Pipeline)

```
URL 입력 → videoId 추출 → Source 레코드 생성 → Celery 태스크 디스패치
                                                       │
              ┌────────────────────────────────────────┘
              ▼
   ① 메타데이터 조회 (oembed / YouTube Data API)
   ② 자막 확보 (youtube-transcript-api, 실패 시 STT fallback)
   ③ 텍스트 정규화 (노이즈 제거, 타임스탬프 정리)
   ④ 청크 분할 (토큰 기반, 오버랩 적용)
   ⑤ 임베딩 생성 (OpenAI text-embedding-3-small)
   ⑥ 요약 생성 (gpt-4o-mini)
   ⑦ 상태 업데이트: ready / partial_ready / failed
```

### 2. 질문 응답 (Q&A Pipeline)

```
질문 입력 → 질문 임베딩 → pgvector 코사인 유사도 검색 (top-k)
              → 검색된 세그먼트 기반 LLM 답변 생성
              → Citation(타임스탬프 근거) 포함 응답 반환
```

## 상태 머신

| 상태 | 설명 |
|------|------|
| `pending` | 소스 등록됨, 처리 대기 |
| `processing` | Ingest 파이프라인 실행 중 |
| `ready` | 모든 처리 완료, 질문 가능 |
| `partial_ready` | 요약 생성 실패했으나 질문은 가능 |
| `failed` | 처리 실패 |

## API 문서 (Swagger UI)

서버 실행 후 브라우저에서 아래 URL로 접속하면 **인터랙티브 API 문서**를 확인할 수 있습니다.

| 문서 | URL | 설명 |
|------|-----|------|
| **Swagger UI** | http://localhost:8000/docs | 인터랙티브 API 테스트 (Try it out) |
| **ReDoc** | http://localhost:8000/redoc | 읽기 편한 API 레퍼런스 |
| **OpenAPI JSON** | http://localhost:8000/openapi.json | OpenAPI 3.1 스펙 (자동 생성) |

Swagger UI에서는 각 엔드포인트의 요청/응답 스키마, 필드 설명, 예시값을 확인하고 직접 API를 호출해볼 수 있습니다.

## API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/health` | 헬스 체크 |
| `POST` | `/api/v1/sources/youtube` | YouTube URL로 소스 등록 |
| `GET` | `/api/v1/sources/{sourceId}` | 소스 상태 및 메타데이터 조회 |
| `GET` | `/api/v1/sources/{sourceId}/segments` | 세그먼트 목록 조회 (디버깅용) |
| `POST` | `/api/v1/chat/ask` | 영상 기반 질문 답변 |

## 개발 환경 설정

```bash
# 1. 환경변수 설정
cp .env.example .env
# .env 파일에서 OPENAI_API_KEY 등을 설정

# 2. Docker로 인프라 실행
docker compose up -d postgres redis

# 3. 의존성 설치
pip install -e ".[dev]"

# 4. DB 마이그레이션
alembic upgrade head

# 5. API 서버 실행
uvicorn app.main:app --reload --port 8000

# 6. Celery 워커 실행 (별도 터미널)
celery -A app.worker.celery_app worker --loglevel=info
```

## 설정 항목 (.env)

| 변수 | 설명 | 기본값 |
|------|------|--------|
| `DATABASE_URL` | PostgreSQL 비동기 연결 URL | `postgresql+asyncpg://...` |
| `REDIS_URL` | Redis 연결 URL | `redis://localhost:6379/0` |
| `OPENAI_API_KEY` | OpenAI API 키 (필수) | - |
| `YOUTUBE_API_KEY` | YouTube Data API 키 (선택) | - |
| `EMBEDDING_MODEL` | 임베딩 모델명 | `text-embedding-3-small` |
| `LLM_MODEL` | 답변 생성 모델명 | `gpt-4o-mini` |
| `CHUNK_MAX_TOKENS` | 청크 최대 토큰 수 | `300` |
| `RETRIEVAL_TOP_K` | 검색 시 반환할 상위 세그먼트 수 | `8` |

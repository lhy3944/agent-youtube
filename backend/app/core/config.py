"""
애플리케이션 환경 설정 모듈.

Pydantic Settings를 사용하여 환경변수(.env)에서 설정값을 로드한다.
모든 설정은 Settings 클래스의 인스턴스(settings)를 통해 접근한다.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "YouTube QA Agent"
    DEBUG: bool = False

    # 데이터베이스 연결 URL (비동기용 asyncpg, 동기용 psycopg2)
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/youtube_qa"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/youtube_qa"

    # Celery 브로커 및 결과 저장소로 사용되는 Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # OpenAI API 설정 (임베딩 생성 및 답변 생성에 사용)
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536  # 임베딩 벡터 차원 수
    LLM_MODEL: str = "gpt-4o-mini"  # 답변/요약 생성에 사용할 LLM 모델

    # 청크 분할 설정
    CHUNK_MAX_TOKENS: int = 300  # 하나의 청크에 포함될 최대 토큰 수
    CHUNK_OVERLAP_TOKENS: int = 50  # 인접 청크 간 겹치는 토큰 수 (문맥 유지용)

    # 벡터 검색 시 반환할 상위 세그먼트 수
    RETRIEVAL_TOP_K: int = 8

    # YouTube Data API 키 (선택사항, 없으면 oembed로 대체)
    YOUTUBE_API_KEY: str = ""

    # .env 파일에서 환경변수 자동 로드, 정의되지 않은 필드는 무시
    model_config = {"env_file": ".env", "extra": "ignore"}


# 앱 전역에서 사용하는 설정 싱글턴 인스턴스
settings = Settings()

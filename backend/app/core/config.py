from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    APP_NAME: str = "YouTube QA Agent"
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/youtube_qa"
    DATABASE_URL_SYNC: str = "postgresql://postgres:postgres@localhost:5432/youtube_qa"

    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"

    # OpenAI (for embeddings and answer generation)
    OPENAI_API_KEY: str = ""
    EMBEDDING_MODEL: str = "text-embedding-3-small"
    EMBEDDING_DIMENSIONS: int = 1536
    LLM_MODEL: str = "gpt-4o-mini"

    # Chunking
    CHUNK_MAX_TOKENS: int = 300
    CHUNK_OVERLAP_TOKENS: int = 50

    # Retrieval
    RETRIEVAL_TOP_K: int = 8

    # YouTube
    YOUTUBE_API_KEY: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()

import os
from pydantic import BaseModel
from dotenv import load_dotenv

# Load local .env if present
load_dotenv()


class Settings(BaseModel):
    PROJECT_NAME: str = "Legal Information Navigator"
    VERSION: str = "1.0.0"
    API_PREFIX: str = "/api"

    # Google Cloud / Gemini configuration
    # Can be provided via GEMINI_API_KEY or Vertex AI ADC
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    GOOGLE_CLOUD_PROJECT: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    VERTEX_AI_LOCATION: str = os.getenv("VERTEX_AI_LOCATION", "us-central1")
    USE_VERTEX_AI: bool = os.getenv("USE_VERTEX_AI", "false").lower() in ("true", "1", "yes")

    # Current supported Gemini model IDs (configurable without code changes)
    DEFAULT_FAST_MODEL: str = os.getenv("GEMINI_FAST_MODEL", "gemini-2.5-flash")
    DEFAULT_REASONING_MODEL: str = os.getenv("GEMINI_REASONING_MODEL", "gemini-2.5-pro")
    DEFAULT_EMBEDDING_MODEL: str = os.getenv("GEMINI_EMBEDDING_MODEL", "text-embedding-004")

    # Evidence & Retrieval thresholds
    SIMILARITY_THRESHOLD: float = float(os.getenv("SIMILARITY_THRESHOLD", "0.65"))
    MAX_EVIDENCE_CHUNKS: int = int(os.getenv("MAX_EVIDENCE_CHUNKS", "5"))

    # Environment and evaluation safety settings
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    ENABLE_EVALUATION_ENDPOINT: bool = os.getenv("ENABLE_EVALUATION_ENDPOINT", "false").lower() in ("true", "1", "yes")
    EVALUATION_KEY: str = os.getenv("EVALUATION_KEY", "")

    # Server settings
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "*"
    ]


settings = Settings()

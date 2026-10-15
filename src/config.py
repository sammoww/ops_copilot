"""Application configuration management using Pydantic Settings."""

from functools import lru_cache
from pathlib import Path
from pydantic import Field, SecretStr, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root path (parent of src/)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Application settings schema validated against environment variables."""

    # Secret string ensures raw API keys are never accidentally logged or printed in tracebacks
    openai_api_key: SecretStr = Field(
        ...,
        alias="OPENAI_API_KEY",
        description="OpenAI API key used for text embeddings and LLM calls",
    )

    chroma_persist_dir: str = Field(
        default="./chroma_db",
        alias="CHROMA_PERSIST_DIR",
        description="Local directory path where Chroma vector database persists chunks and embeddings",
    )

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )


@lru_cache
def get_settings() -> Settings:
    """Return a cached singleton instance of Settings."""
    return Settings()


if __name__ == "__main__":
    print("--- OpsCopilot Configuration Validation ---")
    try:
        settings = get_settings()
        raw_key = settings.openai_api_key.get_secret_value()
        masked_key = (
            f"{raw_key[:7]}...{raw_key[-4:]}"
            if len(raw_key) > 11
            else "***"
        )
        print("[SUCCESS] Environment loaded successfully:")
        print(f" - OPENAI_API_KEY:    {masked_key} (SecretStr masked)")
        print(f" - CHROMA_PERSIST_DIR: {settings.chroma_persist_dir}")
        print(f" - ENV FILE PATH:     {settings.model_config.get('env_file')}")
    except ValidationError as err:
        print("[FAILURE] Configuration validation failed:")
        for error in err.errors():
            loc = " -> ".join(str(e) for e in error["loc"])
            print(f" - Field '{loc}': {error['msg']}")
        raise SystemExit(1)

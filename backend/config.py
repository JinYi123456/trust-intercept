"""Central configuration for the TRUST//INTERCEPT backend.

Every value is .env-driven (create a ``.env`` file next to ``backend/`` or set
real environment variables) so API keys and feature flags can be changed
without touching code. Secrets are never hard-coded.

Key environment variables
-------------------------
ANTHROPIC_API_KEY            Claude (Sonnet) primary LLM (leave empty to run without an LLM)
ANTHROPIC_MODEL              default: claude-sonnet-4-5
GEMINI_API_KEY               Gemini fallback LLM
GEMINI_MODEL                 default: gemini-2.5-flash
LLM_PROVIDER                 auto | gonka | featherless | gemini | none
VIRUSTOTAL_API_KEY           URL reputation (free tier)
SAFE_BROWSING_API_KEY        Google Safe Browsing (free tier)
GOOGLE_VISION_API_KEY        Cloud OCR fallback (opt-in)
OCR_CLOUD_FALLBACK           true only if the user opts in; local Tesseract is the default
REDIRECT_MAX_HOPS            default 5 (the blueprint's redirect-walker cap)
ALLOW_OUTBOUND_LOOKUPS       kill-switch so the live demo works fully offline
DB_PATH                      SQLite path; stores REDACTED cases only
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
PROMPTS_DIR = BASE_DIR / "agent" / "prompts"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        # Read .env from the project root OR from backend/ so the server works
        # no matter which directory uvicorn is launched from. Missing files are
        # skipped silently.
        env_file=(str(BASE_DIR.parent / ".env"), str(BASE_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Application ------------------------------------------------------
    app_name: str = "TRUST//INTERCEPT Decision Defence API"
    db_path: str = str(BASE_DIR / "trust-intercept.db")
    # Dev ports 5173-5175 covered so a Vite port auto-fallback never breaks CORS.
    cors_origins: str = (
        "http://localhost:5173,http://127.0.0.1:5173,"
        "http://localhost:5174,http://127.0.0.1:5174,"
        "http://localhost:5175,http://127.0.0.1:5175"
    )

    # --- LLM providers (free/promo credits first; offline always available) ---
    # auto order: Gonka -> Featherless -> Gemini -> deterministic local engine
    llm_provider: str = "auto"  # auto | gonka | featherless | gemini | none
    gonka_api_key: str = ""
    gonka_model: str = "MiniMaxAI/MiniMax-M2.7"
    gonka_base_url: str = "https://api.gonkarouter.io/v1/messages"
    featherless_api_key: str = ""
    featherless_model: str = "Qwen/Qwen2.5-7B-Instruct"
    featherless_base_url: str = "https://api.featherless.ai/v1/chat/completions"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-3.8-flash"
    gemini_audio_model: str = "gemini-3.8-flash"  # native multimodal audio analysis
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/models"
    llm_timeout_seconds: float = 45.0
    llm_max_tokens: int = 1400

    # --- Evidence normalisation -------------------------------------------
    redirect_max_hops: int = 5
    outbound_timeout_seconds: float = 10.0
    ocr_cloud_fallback: bool = False  # opt-in only; local Tesseract is the default
    google_vision_api_key: str = ""
    max_image_bytes: int = 10 * 1024 * 1024
    max_audio_bytes: int = 20 * 1024 * 1024  # voice calls / voicemails (mp3/wav/m4a)

    # --- Reputation lookups ------------------------------------------------
    virustotal_api_key: str = ""
    safe_browsing_api_key: str = ""
    reputation_cache_ttl_seconds: int = 900

    # --- Demo safety -------------------------------------------------------
    allow_outbound_lookups: bool = True  # set to false for a fully offline demo


@lru_cache
def get_settings() -> Settings:
    return Settings()


def cors_origin_list() -> list[str]:
    return [origin.strip() for origin in get_settings().cors_origins.split(",") if origin.strip()]

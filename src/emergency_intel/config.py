from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
OUTPUTS_DIR = ROOT_DIR / "outputs" / "weekly"


def _load_env_file() -> None:
    for env_name in (".env", ".env.local"):
        env_path = ROOT_DIR / env_name
        if not env_path.exists():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, value = stripped.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key:
                os.environ.setdefault(key, value)


_load_env_file()


@dataclass(frozen=True)
class Settings:
    provider: str = os.getenv("EI_PROVIDER", "mock")
    model: str = os.getenv("EI_MODEL", "mock-structured-v1")
    api_base: str = os.getenv("EI_API_BASE", "https://api.openai.com/v1/chat/completions")
    api_key: str = os.getenv("EI_API_KEY", "")
    x_bearer_token: str = os.getenv("EI_X_BEARER_TOKEN", "")
    x_api_key: str = os.getenv("EI_X_API_KEY", "")
    x_api_secret: str = os.getenv("EI_X_API_SECRET", "")
    x_client_id: str = os.getenv("EI_X_CLIENT_ID", "")
    x_client_secret: str = os.getenv("EI_X_CLIENT_SECRET", "")
    x_access_token: str = os.getenv("EI_X_ACCESS_TOKEN", "")
    x_access_token_secret: str = os.getenv("EI_X_ACCESS_TOKEN_SECRET", "")
    analysis_min_score: float = float(os.getenv("EI_ANALYSIS_MIN_SCORE", "6.0"))
    collect_timeout_seconds: int = int(os.getenv("EI_COLLECT_TIMEOUT_SECONDS", "20"))
    enrich_timeout_seconds: int = int(os.getenv("EI_ENRICH_TIMEOUT_SECONDS", "15"))
    llm_timeout_seconds: int = int(os.getenv("EI_LLM_TIMEOUT_SECONDS", "30"))
    schedule_weekday: str = os.getenv("EI_SCHEDULE_WEEKDAY", "MON").upper()
    schedule_hour: int = int(os.getenv("EI_SCHEDULE_HOUR", "9"))
    timezone: str = os.getenv("EI_TIMEZONE", "Asia/Shanghai")

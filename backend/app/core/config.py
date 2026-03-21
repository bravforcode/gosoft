from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


BACKEND_ROOT = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_ROOT / ".env"


class Settings(BaseSettings):
    APP_NAME: str = "Smart Inventory Vision"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = False

    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7
    API_KEY: str

    DATABASE_URL: str = "sqlite+aiosqlite:///./data/siv.db"

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_CACHE_TTL: int = 30

    CAMERA_0_URL: str = "0"
    CAMERA_1_URL: str | None = None
    CAMERA_2_URL: str | None = None
    CAMERA_3_URL: str | None = None
    CAMERA_0_NAME: str = "CAM-01"
    CAMERA_1_NAME: str = "CAM-02"
    CAMERA_2_NAME: str = "CAM-03"
    CAMERA_3_NAME: str = "CAM-04"
    CAMERA_0_ZONE: str = "Zone A"
    CAMERA_1_ZONE: str = "Zone B"
    CAMERA_2_ZONE: str = "Zone C"
    CAMERA_3_ZONE: str = "Zone D"
    CAMERA_PROCESSING_FPS: float = 2.0
    CAMERA_DISPLAY_FPS: float = 25.0

    YOLO_MODEL_PATH: str = "yolov8n.pt"
    YOLO_CONFIDENCE_THRESHOLD: float = 0.45
    CLAUDE_API_KEY: str | None = None
    CLAUDE_MODEL: str = "claude-sonnet-4-20250514"
    CLAUDE_VISION_ENABLED: bool = True
    CLAUDE_ANALYSIS_INTERVAL: int = 10
    CLAUDE_CACHE_SECONDS: int = 30

    LINE_NOTIFY_TOKEN: str | None = None
    SMTP_HOST: str | None = None
    SMTP_PORT: int | None = None
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    GOSOFT_ERP_URL: str | None = None
    GOSOFT_ERP_API_KEY: str | None = None
    SAP_B1_SERVICE_URL: str | None = None
    SAP_B1_USERNAME: str | None = None
    SAP_B1_PASSWORD: str | None = None
    WEBHOOK_URL: str | None = None

    STOCK_LOW_THRESHOLD: float = 0.50
    STOCK_CRITICAL_THRESHOLD: float = 0.25
    STOCK_EMPTY_THRESHOLD: float = 0.10
    AUTO_PO_APPROVAL_LIMIT: float = 5000.0

    ALLOWED_ORIGINS: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:5175",
            "http://localhost:5175",
            "http://127.0.0.1:5173",
            "http://localhost:5173",
            "http://localhost:3000",
            "http://localhost",
        ]
    )

    EVIDENCE_ROOT: str = "data/evidence"
    DEMO_MODE: bool = True
    SKIP_STARTUP_TASKS: bool = False

    model_config = SettingsConfigDict(env_file=ENV_FILE, case_sensitive=True, extra="ignore")

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"", "0", "false", "no", "off", "release", "prod", "production"}:
                return False
            if normalized in {"1", "true", "yes", "on", "debug", "dev", "development"}:
                return True
        return value

    @field_validator("SMTP_PORT", mode="before")
    @classmethod
    def normalize_optional_port(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url(cls, value: object) -> object:
        if not isinstance(value, str):
            return value
        prefixes = ("sqlite+aiosqlite:///", "sqlite:///")
        for prefix in prefixes:
            if value.startswith(prefix):
                raw_path = value[len(prefix) :]
                candidate = Path(raw_path)
                if not candidate.is_absolute():
                    resolved = (BACKEND_ROOT / candidate).resolve().as_posix()
                    return f"{prefix}{resolved}"
        return value

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def normalize_allowed_origins(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return value
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value

    @property
    def configured_cameras(self) -> list[dict[str, str]]:
        cameras: list[dict[str, str]] = []
        for index in range(4):
            url = getattr(self, f"CAMERA_{index}_URL")
            if not url:
                continue
            cameras.append(
                {
                    "id": f"CAM-{index + 1:02d}",
                    "url": url,
                    "name": getattr(self, f"CAMERA_{index}_NAME"),
                    "zone": getattr(self, f"CAMERA_{index}_ZONE"),
                }
            )
        return cameras


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

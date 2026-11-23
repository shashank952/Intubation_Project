from pydantic_settings import BaseSettings
from typing import Literal, Optional


class Settings(BaseSettings):
    app_name: str = "Airway Assessment API"
    app_version: str = "2.1.0"
    debug: bool = False

    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "airway_db"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

    # Server-enforced sliding session expiry. A session dies after this many
    # idle minutes (no requests) or the absolute cap, whichever comes first.
    session_idle_timeout_minutes: int = 30
    session_absolute_timeout_hours: int = 12
    session_warning_seconds: int = 120
    session_touch_interval_seconds: int = 60

    # Comma-separated allowed browser origins. Never use "*" in production.
    cors_origins: str = (
        "http://localhost:3000,http://127.0.0.1:3000,"
        "https://intubation-project.vercel.app"
    )
    # Regex for this project's Vercel preview deployments.
    cors_origin_regex: str = (
        r"https://intubation-project-[a-z0-9-]+-shashanks-projects-564d08b3\.vercel\.app"
    )

    llm_api_url: str = "https://openrouter.ai/api/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen/qwen-2.5-72b-instruct"
    llm_temperature: float = 0.3
    llm_max_tokens: int = 1024
    # Per-HTTP-attempt timeout. The OpenAI SDK's own retries are disabled so
    # this is the only per-attempt bound.
    llm_timeout: float = 20.0
    llm_retries: int = 1
    # Hard wall-clock cap for the whole summary+recommendations step. Exceeding
    # it returns canned fallback text instead of hanging the prediction request.
    # Must stay comfortably below the clients' abort timeout (240s).
    llm_report_budget_seconds: float = 40.0
    llm_external_enabled: bool = True

    model_checkpoint: str = "checkpoints/tabular_best.pt"
    model_device: str = "cpu"
    # Fail to start when the checkpoint is missing/mismatched. Set false ONLY
    # for local development — the API then serves random weights (flagged in
    # /ready and logs) and must never be used in production.
    model_required: bool = True
    # Softmax temperature. Label smoothing in train_tabular.py already keeps the
    # logits calibrated, so the optimal temperature is 1.0 (no extra scaling).
    model_softmax_temperature: float = 1.0

    prediction_model: Literal["real", "synthetic"] = "real"

    # Trust X-Forwarded-For for rate limiting only behind a trusted TLS proxy.
    behind_proxy: bool = False
    # Reject non-HTTPS requests; enable only behind a TLS-terminating proxy.
    enforce_https: bool = False

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()

# ponytail: dev-safe backstop — never sign JWTs with a publicly-known default secret.
# If JWT_SECRET is unset (or still the placeholder), generate a random per-boot secret.
if settings.jwt_secret in ("", "change-me-in-production"):
    import secrets

    settings.jwt_secret = secrets.token_urlsafe(32)

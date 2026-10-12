from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    app_name: str = "Airway Assessment API"
    app_version: str = "2.0.0"
    debug: bool = False

    mongo_url: str = "mongodb://localhost:27017"
    mongo_db: str = "airway_db"

    jwt_secret: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480

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
    llm_max_tokens: int = 512
    llm_timeout: float = 15.0
    llm_retries: int = 1

    model_checkpoint: str = "checkpoints/tabular_best.pt"
    model_device: str = "cpu"

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

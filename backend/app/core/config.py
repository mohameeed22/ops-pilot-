from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI DevOps Autopilot"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = True

    # GitHub App config
    GITHUB_APP_ID: str
    GITHUB_PRIVATE_KEY: str
    GITHUB_WEBHOOK_SECRET: str

    # External integrations
    SLACK_WEBHOOK_URL: str | None = None
    DISCORD_WEBHOOK_URL: str | None = None
    LLM_API_KEY: str | None = None
    LLM_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"

    # Data stores
    REDIS_URL: str = "redis://redis:6379/0"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:devops_password@db:5432/devops_autopilot"

    # CORS – comma-separated list of allowed frontend origins
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://localhost:80"

    # Seed API key for bootstrapping (set in .env on first run)
    SEED_API_KEY: str | None = None

    # JWT Authentication
    JWT_SECRET: str = "change-me-in-production-please"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Ticketing – Jira (optional)
    JIRA_BASE_URL: str | None = None        # e.g. https://yourcompany.atlassian.net
    JIRA_EMAIL: str | None = None
    JIRA_API_TOKEN: str | None = None
    JIRA_PROJECT_KEY: str | None = None     # e.g. OPS

    # SettingsConfigDict defines where the env file is loaded from
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def cors_origins_list(self) -> List[str]:
        """Returns CORS_ORIGINS as a parsed list."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def formatted_private_key(self) -> str:
        """Returns the private key with properly formatted newlines.

        Handles cases where GITHUB_PRIVATE_KEY is written on a single line
        with literal '\\n' characters in environment configurations.
        """
        return self.GITHUB_PRIVATE_KEY.replace("\\n", "\n")


settings = Settings()

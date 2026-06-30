from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

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

    # Data stores
    REDIS_URL: str = "redis://redis:6379/0"
    DATABASE_URL: str = "postgresql+asyncpg://postgres:devops_password@db:5432/devops_autopilot"

    # SettingsConfigDict defines where the env file is loaded from
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    @property
    def formatted_private_key(self) -> str:
        """Returns the private key with properly formatted newlines.
        
        Handles cases where GITHUB_PRIVATE_KEY is written on a single line 
        with literal '\n' characters in environment configurations.
        """
        return self.GITHUB_PRIVATE_KEY.replace("\\n", "\n")

settings = Settings()

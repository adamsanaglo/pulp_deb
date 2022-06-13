from typing import Any, Optional

from pydantic import BaseSettings, PostgresDsn


class Settings(BaseSettings):
    SERVER_HOST: str
    SERVER_PORT: int
    API_PREFIX: str = "/api/v4"
    DEBUG: bool
    PROJECT_NAME: str = "pmcserver"
    VERSION: str = "0.0.1"

    PULP_HOST: str
    PULP_API_PATH: str = "/pulp/api/v3"
    PULP_USERNAME: str
    PULP_PASSWORD: str

    POSTGRES_SERVER: str
    POSTGRES_USER: str
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str
    LOGGING_CONFIG: Optional[str]

    def db_uri(self) -> Any:
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            user=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            path=f"/{self.POSTGRES_DB or ''}",
        )

    class Config:
        env_file = ".env"


settings = Settings()

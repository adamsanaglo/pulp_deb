from pydantic import BaseSettings


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

    LOGGING_CONFIG: str = "/pmcserver/app/logging.conf"

    class Config:
        env_file = ".env"


settings = Settings()

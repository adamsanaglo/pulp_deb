import ssl
from typing import Any, Dict, Optional

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
    POSTGRES_SERVER_CA_CERT: str = ""
    LOGGING_CONFIG: Optional[str]

    APP_CLIENT_ID: str = ""
    TENANT_ID: str = ""

    # TODO: [MIGRATE] Remove me.
    AF_QUEUE_ACTION_URL: str = ""

    def db_uri(self) -> Any:
        return PostgresDsn.build(
            scheme="postgresql+asyncpg",
            user=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_SERVER,
            path=f"/{self.POSTGRES_DB or ''}",
        )

    def db_engine_args(self) -> Dict[str, Any]:
        ret: Dict[str, Any] = {"echo": True, "future": True}
        if not self.DEBUG:
            # Enforce extra tls checks if not in dev environment.
            # Let's validate that the ssl cert the server is providing is actually signed by
            # (a delegate of) DigiCert and actually corresponds to our postgres server's hostname.
            # https://docs.microsoft.com/en-us/azure/postgresql/flexible-server/how-to-connect-tls-ssl#applications-that-require-certificate-verification-for-tlsssl-connectivity
            if not self.POSTGRES_SERVER_CA_CERT:
                # If cafile is not provided, _even if_ you've set verify_mode=CERT_REQUIRED, it will
                # silently fallback to a non-verified tls connection. That's not what we want,
                # we want the cert to actually be REQUIRED (and verified).
                raise Exception("Postgres server ca cert not set")

            ssl_ctx = ssl.create_default_context(
                ssl.Purpose.SERVER_AUTH, cafile=self.POSTGRES_SERVER_CA_CERT
            )
            ssl_ctx.verify_mode = ssl.CERT_REQUIRED
            ssl_ctx.check_hostname = True
            ret["connect_args"] = {"ssl": ssl_ctx}

        return ret

    class Config:
        env_file = ".env"


settings = Settings()

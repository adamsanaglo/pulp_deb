import logging
from pydantic import BaseSettings
import sys

from asgi_correlation_id import CorrelationIdFilter


class Settings(BaseSettings):
    KEYVAULT: str
    AUTH_CERT_PATH: str  # path to the on-disk esrp auth cert
    SIGN_CERT: str
    LEGACY_KEY_PATH: str  # path to the on-disk private legacy signing key
    APP_ID: str
    TENANT_ID: str
    # Separate multiple key-codes with ';'
    KEY_CODES: str = ""
    LEGACY_KEY_THUMBPRINT: str = ""

    class Config:
        env_file = ".env"


settings = Settings()


FORMAT = (
    "signer %(asctime)s %(levelname)-7s [%(correlation_id)s]: %(name)s:%(lineno)d - %(message)s"
)
logging.basicConfig(level=logging.INFO, format=FORMAT, stream=sys.stdout)
log = logging.getLogger("signer")
log.addFilter(CorrelationIdFilter("correlation_id", 32))


def is_valid_keycode(key_id: str) -> bool:
    key_codes = settings.KEY_CODES.split(";")
    return key_id in key_codes

from pydantic import BaseSettings


class Settings(BaseSettings):
    KEYVAULT: str
    AUTH_CERT: str
    SIGN_CERT: str
    LEGACY_KEY: str # Name of the legacy key in keyvault
    APP_ID: str
    TENANT_ID: str
    # Separate multiple key-codes with ';'
    KEY_CODES: str = ""
    LEGACY_KEY_THUMBPRINT: str = ""

    class Config:
        env_file = ".env"


settings = Settings()


def is_valid_keycode(key_id: str) -> bool:
    key_codes = settings.KEY_CODES.split(';')
    return key_id in key_codes
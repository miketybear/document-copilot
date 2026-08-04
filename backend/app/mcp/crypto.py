from cryptography.fernet import Fernet

from app.config import settings

_fernet = Fernet(settings.mcp_token_encryption_key)


def encrypt(value: str) -> str:
    return _fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt(value: str) -> str:
    return _fernet.decrypt(value.encode("utf-8")).decode("utf-8")

import hashlib
import hmac
import os
import secrets


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 390000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt, expected = stored_hash.split("$", 1)
    except ValueError:
        return False

    calculated = hash_password(password, salt).split("$", 1)[1]
    return hmac.compare_digest(calculated, expected)


def new_session_token() -> str:
    return secrets.token_urlsafe(32)


def get_session_secret() -> str:
    return os.getenv("SESSION_SECRET", "change-this-secret")


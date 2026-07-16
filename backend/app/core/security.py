import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

SECRET_KEY = os.getenv(
    "JWT_SECRET",
    os.getenv("SECRET_KEY", "local-development-secret-change-me-32"),
)
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRES_MINUTES", "1440"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=15))
    return jwt.encode({**data, "iat": now, "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)

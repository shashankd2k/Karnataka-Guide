"""
Security primitives: Argon2id password hashing and PyJWT token utilities.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional, Tuple
import uuid
import argon2
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
import jwt
from app.core.config import get_settings
from app.core.errors import UnauthorizedException

# Industry-standard Argon2id password hasher
_hasher = argon2.PasswordHasher(
    time_cost=3,
    memory_cost=65536,  # 64 MB
    parallelism=4,
    hash_len=32,
    type=argon2.Type.ID,
)


def hash_password(plain_password: str) -> str:
    """Hash plain-text password using Argon2id."""
    return _hasher.hash(plain_password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify plain-text password against Argon2id hash with constant-time protection."""
    try:
        return _hasher.verify(hashed_password, plain_password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def create_access_token(
    admin_id: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Generate signed JWT access token with JTI and sub claims."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)

    jti = uuid.uuid4().hex
    payload: Dict[str, Any] = {
        "sub": admin_id,
        "role": role,
        "type": "access",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": jti,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(
    admin_id: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> Tuple[str, str]:
    """Generate signed JWT refresh token, returning (token_str, jti)."""
    settings = get_settings()
    now = datetime.now(timezone.utc)
    if expires_delta is not None:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

    jti = uuid.uuid4().hex
    payload: Dict[str, Any] = {
        "sub": admin_id,
        "role": role,
        "type": "refresh",
        "iat": int(now.timestamp()),
        "exp": int(expire.timestamp()),
        "jti": jti,
    }
    token_str = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token_str, jti


def decode_token(token: str, expected_type: Optional[str] = None) -> Dict[str, Any]:
    """
    Decode and cryptographically verify JWT token claims.
    Raises UnauthorizedException if expired, invalid, or mismatched token type.
    """
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"require": ["sub", "role", "type", "exp", "iat", "jti"]},
        )
    except jwt.ExpiredSignatureError:
        raise UnauthorizedException("Token has expired.")
    except jwt.InvalidTokenError:
        raise UnauthorizedException("Invalid token signature or payload.")

    token_type = payload.get("type")
    if expected_type and token_type != expected_type:
        raise UnauthorizedException(
            f"Invalid token type. Expected '{expected_type}' token."
        )

    return payload

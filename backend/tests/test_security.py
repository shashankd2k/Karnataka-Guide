"""
Unit tests for cryptographic security primitives: Argon2id password hashing and PyJWT tokens.
"""

from datetime import timedelta
import pytest
import jwt
from app.core.config import get_settings
from app.core.errors import UnauthorizedException
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_argon2id_password_hashing_and_verification():
    """Verify Argon2id hashing generates valid hashes and verifies correctly."""
    plain = "SecureKarnatakaPassword2026!"
    hashed = hash_password(plain)
    assert hashed.startswith("$argon2id$")
    assert hashed != plain

    assert verify_password(plain, hashed) is True
    assert verify_password("WrongPassword123", hashed) is False
    assert verify_password("", hashed) is False


def test_access_token_creation_and_claims():
    """Verify access token contains expected claims."""
    admin_id = "admin-12345"
    role = "SUPER_ADMIN"
    token = create_access_token(admin_id=admin_id, role=role)

    payload = decode_token(token, expected_type="access")
    assert payload["sub"] == admin_id
    assert payload["role"] == role
    assert payload["type"] == "access"
    assert "jti" in payload
    assert "exp" in payload
    assert "iat" in payload


def test_refresh_token_creation_and_jti():
    """Verify refresh token generation returns distinct JTI and refresh type."""
    admin_id = "admin-67890"
    role = "SITE_CURATOR"
    token_str, jti = create_refresh_token(admin_id=admin_id, role=role)

    payload = decode_token(token_str, expected_type="refresh")
    assert payload["sub"] == admin_id
    assert payload["role"] == role
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti


def test_token_expiration_rejection():
    """Verify expired token raises UnauthorizedException."""
    token = create_access_token(
        admin_id="admin-exp",
        role="OPERATOR",
        expires_delta=timedelta(seconds=-10),  # expired 10 seconds ago
    )
    with pytest.raises(UnauthorizedException) as exc_info:
        decode_token(token, expected_type="access")
    assert "expired" in str(exc_info.value.message).lower()


def test_wrong_token_type_rejection():
    """Verify refresh token cannot be used as an access token."""
    refresh_token_str, _ = create_refresh_token(admin_id="admin-type", role="VIEWER")
    with pytest.raises(UnauthorizedException) as exc_info:
        decode_token(refresh_token_str, expected_type="access")
    assert "invalid token type" in str(exc_info.value.message).lower()


def test_malformed_token_rejection():
    """Verify malformed strings raise UnauthorizedException."""
    with pytest.raises(UnauthorizedException):
        decode_token("not.a.valid.jwt.token", expected_type="access")


def test_invalid_signature_rejection():
    """Verify tampering with token payload or using wrong secret key fails signature check."""
    settings = get_settings()
    # Sign with a different secret
    forged_token = jwt.encode(
        {"sub": "admin-hacker", "role": "SUPER_ADMIN", "type": "access", "exp": 9999999999, "iat": 1000, "jti": "abc"},
        "wrong-secret-key-12345678901234567890",
        algorithm="HS256",
    )
    with pytest.raises(UnauthorizedException) as exc_info:
        decode_token(forged_token, expected_type="access")
    assert "invalid token" in str(exc_info.value.message).lower()

"""
Unit tests for database configuration and connection URL building.
"""

from app.core.config import Settings


def test_default_database_settings():
    """Verify default database configuration parameters."""
    settings = Settings(_env_file=None)
    assert settings.DB_HOST == "127.0.0.1"
    assert settings.DB_PORT == 3306
    assert settings.DB_USER == "root"
    assert settings.DB_NAME == "karnataka_guide"
    assert settings.DB_POOL_SIZE == 5
    assert settings.DB_MAX_OVERFLOW == 10
    assert settings.DB_POOL_TIMEOUT == 30.0
    assert settings.DB_POOL_RECYCLE == 1800


def test_async_database_url_construction():
    """Verify async MySQL URL uses asyncmy dialect."""
    settings = Settings(
        DB_HOST="db.internal.karnataka.gov.in",
        DB_PORT=3307,
        DB_USER="guide_admin",
        DB_PASSWORD="secure_password_123",
        DB_NAME="kg_production",
    )
    url = settings.async_database_url
    assert url.startswith("mysql+asyncmy://guide_admin:secure_password_123@db.internal.karnataka.gov.in:3307/kg_production")
    assert "charset=utf8mb4" in url


def test_special_characters_in_password_escaped():
    """Verify URL encoding for passwords containing special characters."""
    settings = Settings(
        DB_USER="admin@user",
        DB_PASSWORD="p@ssword#123/special?&",
    )
    url = settings.async_database_url
    assert "p%40ssword%23123%2Fspecial%3F%26" in url
    assert "admin%40user" in url

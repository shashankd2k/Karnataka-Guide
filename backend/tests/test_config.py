"""
Unit tests for configuration loading and deployment profiles.
"""

import pytest
from pydantic import ValidationError
from app.core.config import AppProfile, Settings, get_settings


def test_default_settings():
    """Verify default settings values."""
    settings = Settings()
    assert settings.PROJECT_NAME == "AI-Powered Smart Tourist Guide Platform for Karnataka"
    assert settings.VERSION == "0.1.0"
    assert settings.API_V1_STR == "/api/v1"
    assert settings.APP_PROFILE in (AppProfile.DEV, AppProfile.STANDALONE, AppProfile.CLOUD)
    assert isinstance(settings.CORS_ORIGINS, list)
    assert len(settings.CORS_ORIGINS) > 0


@pytest.mark.parametrize(
    "profile_input,expected_enum",
    [
        ("dev", AppProfile.DEV),
        ("DEV", AppProfile.DEV),
        ("standalone", AppProfile.STANDALONE),
        ("STANDALONE", AppProfile.STANDALONE),
        ("cloud", AppProfile.CLOUD),
        ("CLOUD", AppProfile.CLOUD),
    ],
)
def test_valid_app_profiles(profile_input, expected_enum):
    """Verify that all three valid deployment profiles are parsed correctly."""
    settings = Settings(APP_PROFILE=profile_input)
    assert settings.APP_PROFILE == expected_enum


def test_invalid_app_profile_rejected():
    """Verify that unsupported deployment profiles are strictly rejected."""
    with pytest.raises(ValidationError) as exc_info:
        Settings(APP_PROFILE="unsupported_hardware_profile")
    assert "Invalid APP_PROFILE" in str(exc_info.value)


def test_cors_origins_string_parsing():
    """Verify comma-separated string parsing for CORS origins."""
    settings = Settings(CORS_ORIGINS="http://example.com, http://app.karnataka.gov.in")  # type: ignore[arg-type]
    assert settings.CORS_ORIGINS == ["http://example.com", "http://app.karnataka.gov.in"]


def test_get_settings_caching():
    """Verify that get_settings() returns a cached singleton instance."""
    s1 = get_settings()
    s2 = get_settings()
    assert s1 is s2

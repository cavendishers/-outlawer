import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_production_settings_reject_default_secret() -> None:
    with pytest.raises(ValidationError, match="SECRET_KEY"):
        Settings(
            _env_file=None,
            environment="production",
            secret_key="change-me",
            bootstrap_admin_username="admin",
            bootstrap_admin_password="strong-password",
        )


def test_production_settings_accept_explicit_secrets() -> None:
    settings = Settings(
        _env_file=None,
        environment="production",
        secret_key="0123456789abcdef0123456789abcdef",
    )

    assert settings.environment == "production"

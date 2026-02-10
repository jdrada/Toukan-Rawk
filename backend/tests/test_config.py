"""Tests for app.config."""

import pytest

from app.config import Settings


class TestSettings:
    def test_default_values(self):
        s = Settings()
        assert s.db_host == "localhost"
        assert s.db_port == 5432
        assert s.db_name == "rawk_db"
        assert s.environment == "development"
        assert s.debug is True

    def test_database_url_property(self):
        s = Settings(db_user="user", db_password="pass", db_host="db.example.com", db_port=5433, db_name="mydb")
        assert s.database_url == "postgresql+asyncpg://user:pass@db.example.com:5433/mydb"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("DB_HOST", "custom-host")
        monkeypatch.setenv("DEBUG", "false")
        s = Settings()
        assert s.db_host == "custom-host"
        assert s.debug is False

from datetime import date
from pathlib import Path

from oura_dash.config import Settings


def test_defaults_and_env(monkeypatch):
    monkeypatch.setenv("OURA_TOKEN", "abc")
    s = Settings()
    assert s.token == "abc"
    assert s.window_start == date(2026, 6, 16)
    assert s.window_end == date(2026, 9, 1)
    assert s.base_url == "https://api.ouraring.com"
    assert s.db_path == Path("oura.db")


def test_current_day_uses_injected_today(monkeypatch):
    monkeypatch.setenv("OURA_TOKEN", "abc")
    s = Settings(today=date(2026, 7, 6))
    assert s.current_day() == date(2026, 7, 6)


def test_env_overrides_window(monkeypatch):
    monkeypatch.setenv("OURA_TOKEN", "abc")
    monkeypatch.setenv("OURA_WINDOW_START", "2025-01-01")
    assert Settings().window_start == date(2025, 1, 1)

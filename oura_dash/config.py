from datetime import date
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OURA_", env_file=".env", extra="ignore")

    token: str
    db_path: Path = Path("oura.db")
    base_url: str = "https://api.ouraring.com"
    window_start: date = date(2026, 6, 16)
    window_end: date = date(2026, 9, 1)
    history_start: date = date(2016, 1, 1)
    today: date | None = None

    def current_day(self) -> date:
        return self.today or date.today()

from datetime import date

from typer.testing import CliRunner

from oura_dash import cli
from oura_dash.config import Settings
from oura_dash.storage import Storage

runner = CliRunner()


def test_stats_command_prints_table(monkeypatch, tmp_path):
    db = tmp_path / "t.db"
    with Storage(db) as st:
        st.init_schema()
        st.upsert("sleep", [
            {"id": f"b{i}", "day": f"2026-01-0{i+1}", "average_hrv": 40 + i} for i in range(5)
        ])
        st.upsert("sleep", [
            {"id": f"w{i}", "day": f"2026-06-2{i}", "average_hrv": 60 + i} for i in range(5)
        ])
    monkeypatch.setattr(cli, "_make_settings",
                        lambda: Settings(token="x", db_path=db, today=date(2026, 9, 2)))
    result = runner.invoke(cli.app, ["stats"])
    assert result.exit_code == 0
    assert "average_hrv" in result.stdout


def test_sync_command_reports_counts(monkeypatch, tmp_path):
    db = tmp_path / "t.db"
    monkeypatch.setattr(cli, "_make_settings",
                        lambda: Settings(token="x", db_path=db, today=date(2026, 7, 6)))

    class FakeClient:
        def fetch(self, endpoint, start, end):
            return [{"id": "a", "day": "2026-07-01"}] if "daily_stress" in endpoint else []

    monkeypatch.setattr(cli, "_make_client", lambda s: FakeClient())
    result = runner.invoke(cli.app, ["sync"])
    assert result.exit_code == 0
    assert "daily_stress" in result.stdout

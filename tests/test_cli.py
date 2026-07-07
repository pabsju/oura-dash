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
            {"id": f"b{i}", "day": f"2026-01-0{i+1}", "average_hrv": 40 + i, "type": "long_sleep"}
            for i in range(5)
        ])
        st.upsert("sleep", [
            {"id": f"w{i}", "day": f"2026-06-2{i}", "average_hrv": 60 + i, "type": "long_sleep"}
            for i in range(5)
        ])
    monkeypatch.setattr(cli, "_make_settings",
                        lambda: Settings(token="x", db_path=db, today=date(2026, 9, 2)))
    result = runner.invoke(cli.app, ["stats"])
    assert result.exit_code == 0
    assert "average_hrv" in result.stdout


def test_stats_prints_both_baseline_tables(monkeypatch, tmp_path):
    db = tmp_path / "t.db"
    with Storage(db) as st:
        st.init_schema()
        st.upsert("sleep", [
            {"id": f"b{i}", "day": f"2026-01-0{i+1}", "average_hrv": 40 + i, "type": "long_sleep"}
            for i in range(5)
        ])
        st.upsert("sleep", [
            {"id": f"w{i}", "day": f"2026-06-2{i}", "average_hrv": 60 + i, "type": "long_sleep"}
            for i in range(5)
        ])
    monkeypatch.setattr(cli, "_make_settings",
                        lambda: Settings(token="x", db_path=db, today=date(2026, 9, 2)))
    result = runner.invoke(cli.app, ["stats", "--baseline-start", "2026-01-03"])
    assert result.exit_code == 0
    assert "vs all history" in result.stdout
    assert "vs baseline window (2026-01-03" in result.stdout
    # bounded table has n_base 3, all-history table has 5
    assert result.stdout.count("average_hrv") == 2


def test_stats_on_fresh_db_does_not_crash(monkeypatch, tmp_path):
    db = tmp_path / "fresh.db"
    monkeypatch.setattr(cli, "_make_settings",
                        lambda: Settings(token="x", db_path=db, today=date(2026, 9, 2)))
    result = runner.invoke(cli.app, ["stats"])
    assert result.exit_code == 0
    assert "metric" in result.stdout


def test_serve_invokes_streamlit(monkeypatch):
    calls = []

    def fake_run_streamlit(args):
        calls.append(args)
        return None

    monkeypatch.setattr(cli, "_run_streamlit", fake_run_streamlit)
    result = runner.invoke(cli.app, ["serve"])
    assert result.exit_code == 0
    assert len(calls) == 1
    argv = calls[0]
    assert "streamlit" in argv
    assert "run" in argv
    assert argv[-1].endswith("app.py")


def test_missing_token_friendly_error(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("OURA_TOKEN", raising=False)
    result = runner.invoke(cli.app, ["stats"])
    assert result.exit_code != 0
    assert "OURA_TOKEN" in result.output


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

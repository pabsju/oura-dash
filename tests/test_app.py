import pandas as pd

from oura_dash import app
from oura_dash.stats import BenchmarkReport, MetricResult
from datetime import date


def _frame():
    return pd.DataFrame([
        {"day": pd.Timestamp("2026-06-19"), "metric": "average_hrv", "value": 40.0},
        {"day": pd.Timestamp("2026-06-20"), "metric": "average_hrv", "value": 44.0},
        {"day": pd.Timestamp("2026-06-20"), "metric": "steps", "value": 8000.0},
    ])


def test_latest_values_takes_last_per_metric():
    lv = app.latest_values(_frame())
    hrv = lv[lv.metric == "average_hrv"].iloc[0]
    assert hrv["value"] == 44.0
    assert hrv["day"] == pd.Timestamp("2026-06-20")


def test_trend_figure_has_window_shading():
    fig = app.trend_figure(_frame(), "average_hrv", date(2026, 6, 16), date(2026, 9, 1), "Average HRV")
    assert fig.data[0].y.tolist() == [40.0, 44.0]
    # a shaded vrect exists
    assert any(shape.type == "rect" for shape in fig.layout.shapes)


def test_results_table_columns():
    report = BenchmarkReport(results=[MetricResult(
        metric="average_hrv", n_baseline=10, n_window=5, median_baseline=40, median_window=50,
        cliffs_delta=0.8, ci_low=0.5, ci_high=0.95, u_stat=5.0, p_value=0.01, q_value=0.02,
    )], interim=True)
    tbl = app.results_table(report)
    assert "metric" in tbl.columns
    assert tbl.iloc[0]["metric"] == "average_hrv"


def test_results_table_empty_report_has_columns():
    report = BenchmarkReport(results=[], interim=False)
    tbl = app.results_table(report)
    assert list(tbl.columns) == [
        "metric", "label", "n_baseline", "n_window", "median_baseline", "median_window",
        "cliffs_delta", "ci", "p_value", "q_value",
    ]
    assert len(tbl) == 0


def test_module_imports_without_token(monkeypatch):
    monkeypatch.delenv("OURA_TOKEN", raising=False)
    import importlib
    importlib.reload(app)  # must not raise


def test_render_executes_without_errors(monkeypatch, tmp_path):
    from streamlit.testing.v1 import AppTest

    from oura_dash.storage import Storage

    db_path = tmp_path / "oura.db"
    monkeypatch.setenv("OURA_TOKEN", "dummy")
    monkeypatch.setenv("OURA_DB_PATH", str(db_path))

    with Storage(db_path) as storage:
        storage.init_schema()
        storage.upsert("sleep", [
            {"id": "sleep-1", "day": "2026-01-05", "average_hrv": 50.0},
            {"id": "sleep-2", "day": "2026-06-20", "average_hrv": 55.0},
            {"id": "sleep-3", "day": "2026-06-21", "average_hrv": 60.0},
        ])
        storage.upsert("daily_stress", [
            {"id": "stress-1", "day": "2026-01-05", "stress_high": 50.0},
            {"id": "stress-2", "day": "2026-06-20", "stress_high": 55.0},
            {"id": "stress-3", "day": "2026-06-21", "stress_high": 60.0},
        ])

    # Streamlit auto-derives each `plotly_chart` element's ID from its type and
    # rendered content. Two metrics with genuinely different data/labels never
    # collide on that hash regardless of whether `key=` is set, so a faithful
    # regression test has to force two loop iterations to render byte-identical
    # figures (same day/value series *and* the same label) -- exactly the
    # pathological case a missing `key=` fails to guard against. The fix
    # (`key=f"trend_{key}"`) makes each chart's ID unique regardless of content.
    monkeypatch.setattr(
        "oura_dash.app.metric_labels",
        lambda: {"average_hrv": "Same Label", "stress_high": "Same Label"},
    )

    script = """
import oura_dash.app as app
from oura_dash.config import Settings
from oura_dash.storage import Storage

settings = Settings()
with Storage(settings.db_path) as st:
    app.render(st, settings)
"""
    at = AppTest.from_string(script)
    at.run(timeout=60)
    assert not at.exception, at.exception

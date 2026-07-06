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


def test_module_imports_without_token(monkeypatch):
    monkeypatch.delenv("OURA_TOKEN", raising=False)
    import importlib
    importlib.reload(app)  # must not raise

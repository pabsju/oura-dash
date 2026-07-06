from datetime import date

import pandas as pd

from oura_dash.config import Settings
from oura_dash.stats import benchmark, cliffs_delta


def test_cliffs_delta_extremes():
    assert cliffs_delta([5, 6, 7], [1, 2, 3]) == 1.0
    assert cliffs_delta([1, 2, 3], [5, 6, 7]) == -1.0
    assert abs(cliffs_delta([1, 2, 3], [1, 2, 3])) < 1e-9


def _frame(baseline_vals, window_vals, metric="average_hrv"):
    rows = []
    for i, v in enumerate(baseline_vals):
        rows.append({"day": pd.Timestamp("2026-01-01") + pd.Timedelta(days=i), "metric": metric, "value": v})
    for i, v in enumerate(window_vals):
        rows.append({"day": pd.Timestamp("2026-06-20") + pd.Timedelta(days=i), "metric": metric, "value": v})
    return pd.DataFrame(rows)


def _settings(today=date(2026, 9, 2)):
    return Settings(token="x", today=today, window_start=date(2026, 6, 16), window_end=date(2026, 9, 1))


def test_benchmark_detects_shift():
    frame = _frame([40, 41, 39, 38, 42], [60, 61, 59, 62, 63])
    report = benchmark(frame, _settings(), n_boot=200)
    r = report.results[0]
    assert r.metric == "average_hrv"
    assert r.n_baseline == 5 and r.n_window == 5
    assert r.median_window > r.median_baseline
    assert r.cliffs_delta > 0.9
    assert r.p_value < 0.05
    assert r.ci_low <= r.cliffs_delta <= r.ci_high


def test_interim_flag_true_before_window_end():
    frame = _frame([40, 41, 42], [50, 51, 52])
    report = benchmark(frame, _settings(today=date(2026, 7, 6)), n_boot=50)
    assert report.interim is True


def test_metric_with_too_few_points_skipped():
    frame = _frame([40], [50])  # only 1 point per group
    report = benchmark(frame, _settings(), n_boot=50)
    assert report.results == []

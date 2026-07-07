from datetime import date

import pandas as pd
from statsmodels.stats.multitest import multipletests

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


def test_interim_flag_true_on_window_end_day():
    # window_end's own data is still incomplete on that morning, so it counts as interim.
    frame = _frame([40, 41, 42], [50, 51, 52])
    report = benchmark(frame, _settings(today=date(2026, 9, 1)), n_boot=50)
    assert report.interim is True


def test_interim_flag_false_after_window_end():
    frame = _frame([40, 41, 42], [50, 51, 52])
    report = benchmark(frame, _settings(today=date(2026, 9, 2)), n_boot=50)
    assert report.interim is False


def test_baseline_start_bounds_baseline():
    frame = _frame([40, 41, 39, 38, 42], [60, 61, 59, 62, 63])
    # baseline days run 2026-01-01..2026-01-05; bound at 01-03 keeps 3 of 5
    report = benchmark(frame, _settings(), n_boot=50, baseline_start=date(2026, 1, 3))
    assert report.results[0].n_baseline == 3
    # None keeps full history (current behavior)
    report_all = benchmark(frame, _settings(), n_boot=50, baseline_start=None)
    assert report_all.results[0].n_baseline == 5


def test_baseline_start_after_data_yields_no_results():
    frame = _frame([40, 41, 42], [50, 51, 52])
    report = benchmark(frame, _settings(), n_boot=50, baseline_start=date(2026, 6, 15))
    assert report.results == []


def test_metric_with_too_few_points_skipped():
    frame = _frame([40], [50])  # only 1 point per group
    report = benchmark(frame, _settings(), n_boot=50)
    assert report.results == []


def test_bh_fdr_across_multiple_metrics():
    shifted = _frame([40, 41, 39, 38, 42], [60, 61, 59, 62, 63], metric="average_hrv")
    unshifted = _frame([8000, 8100, 7900, 8050, 7950], [8020, 8080, 7920, 8040, 7960], metric="steps")
    frame = pd.concat([shifted, unshifted], ignore_index=True)

    report = benchmark(frame, _settings(), n_boot=50)

    metrics_seen = {r.metric for r in report.results}
    assert metrics_seen == {"average_hrv", "steps"}

    # BH property: q >= p for every result
    for r in report.results:
        assert r.q_value >= r.p_value - 1e-12

    # Results are sorted by q_value ascending.
    q_values = [r.q_value for r in report.results]
    assert q_values == sorted(q_values)

    # Independently recompute BH-FDR on the same p-values (in results order) and
    # verify alignment between pvals and results is correct.
    pvals = [r.p_value for r in report.results]
    expected_q = multipletests(pvals, method="fdr_bh")[1]
    for r, eq in zip(report.results, expected_q):
        assert abs(r.q_value - eq) < 1e-9

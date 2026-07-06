from dataclasses import dataclass

import numpy as np
import pandas as pd
from numpy.typing import ArrayLike
from scipy.stats import mannwhitneyu
from statsmodels.stats.multitest import multipletests

from oura_dash.config import Settings


@dataclass
class MetricResult:
    metric: str
    n_baseline: int
    n_window: int
    median_baseline: float
    median_window: float
    cliffs_delta: float
    ci_low: float
    ci_high: float
    u_stat: float
    p_value: float
    q_value: float


@dataclass
class BenchmarkReport:
    results: list[MetricResult]
    interim: bool


def cliffs_delta(a: ArrayLike, b: ArrayLike) -> float:
    a_arr = np.asarray(a, dtype=float)
    b_arr = np.asarray(b, dtype=float)
    if a_arr.size == 0 or b_arr.size == 0:
        return 0.0
    diff = a_arr[:, None] - b_arr[None, :]
    greater = int(np.sum(diff > 0))
    less = int(np.sum(diff < 0))
    return (greater - less) / (a_arr.size * b_arr.size)


def _boot_ci(a, b, n_boot, rng):
    if n_boot <= 0:
        return (float("nan"), float("nan"))
    deltas = np.empty(n_boot)
    a_arr, b_arr = np.asarray(a, float), np.asarray(b, float)
    for i in range(n_boot):
        ra = rng.choice(a_arr, size=a_arr.size, replace=True)
        rb = rng.choice(b_arr, size=b_arr.size, replace=True)
        deltas[i] = cliffs_delta(ra, rb)
    return (float(np.percentile(deltas, 2.5)), float(np.percentile(deltas, 97.5)))


def benchmark(
    frame: pd.DataFrame, settings: Settings, *, n_boot: int = 1000, rng_seed: int = 0
) -> BenchmarkReport:
    interim = settings.current_day() <= settings.window_end
    if frame.empty:
        return BenchmarkReport(results=[], interim=interim)

    days = pd.to_datetime(frame["day"])
    ws = pd.Timestamp(settings.window_start)
    we = pd.Timestamp(settings.window_end)
    is_base = days < ws
    is_win = (days >= ws) & (days <= we)

    rng = np.random.default_rng(rng_seed)
    partial: list[MetricResult] = []
    pvals: list[float] = []
    for metric, grp in frame.groupby("metric"):
        base = grp.loc[is_base.loc[grp.index], "value"].to_numpy(float)
        win = grp.loc[is_win.loc[grp.index], "value"].to_numpy(float)
        if base.size < 2 or win.size < 2:
            continue
        u, p = mannwhitneyu(win, base, alternative="two-sided")
        d = cliffs_delta(win, base)
        lo, hi = _boot_ci(win, base, n_boot, rng)
        partial.append(MetricResult(
            metric=str(metric), n_baseline=base.size, n_window=win.size,
            median_baseline=float(np.median(base)), median_window=float(np.median(win)),
            cliffs_delta=d, ci_low=lo, ci_high=hi, u_stat=float(u),
            p_value=float(p), q_value=float("nan"),
        ))
        pvals.append(float(p))

    if pvals:
        q = multipletests(pvals, method="fdr_bh")[1]
        for res, qv in zip(partial, q):
            res.q_value = float(qv)

    partial.sort(key=lambda r: r.q_value)
    return BenchmarkReport(results=partial, interim=interim)

from dataclasses import dataclass
from typing import Any, Callable

import pandas as pd

from oura_dash.storage import Storage


@dataclass(frozen=True)
class MetricDef:
    key: str
    collection: str
    label: str
    unit: str
    direction: str
    extract: Callable[[dict[str, Any]], float | None]


def _num(row: dict[str, Any], field: str) -> float | None:
    v = row.get(field)
    return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None


def _nested_avg(row: dict[str, Any], field: str) -> float | None:
    obj = row.get(field)
    if isinstance(obj, dict):
        v = obj.get("average")
        return float(v) if isinstance(v, (int, float)) and not isinstance(v, bool) else None
    return None


def _f(field: str) -> Callable[[dict[str, Any]], float | None]:
    return lambda row: _num(row, field)


def _long_sleep_num(field: str) -> Callable[[dict[str, Any]], float | None]:
    def extract(row: dict[str, Any]) -> float | None:
        if row.get("type") != "long_sleep":
            return None
        return _num(row, field)

    return extract


METRICS: list[MetricDef] = [
    MetricDef("stress_high", "daily_stress", "High-stress time", "s", "lower_better", _f("stress_high")),
    MetricDef("recovery_high", "daily_stress", "High-recovery time", "s", "higher_better", _f("recovery_high")),
    MetricDef("average_hrv", "sleep", "Average HRV", "ms", "higher_better", _long_sleep_num("average_hrv")),
    MetricDef("average_heart_rate", "sleep", "Avg sleeping HR", "bpm", "lower_better", _long_sleep_num("average_heart_rate")),
    MetricDef("lowest_heart_rate", "sleep", "Lowest HR", "bpm", "lower_better", _long_sleep_num("lowest_heart_rate")),
    MetricDef("sleep_efficiency", "sleep", "Sleep efficiency", "%", "higher_better", _long_sleep_num("efficiency")),
    MetricDef("sleep_score", "daily_sleep", "Sleep score", "", "higher_better", _f("score")),
    MetricDef("readiness_score", "daily_readiness", "Readiness score", "", "higher_better", _f("score")),
    MetricDef("temperature_deviation", "daily_readiness", "Temp deviation", "°C", "neutral", _f("temperature_deviation")),
    MetricDef("steps", "daily_activity", "Steps", "", "higher_better", _f("steps")),
    MetricDef("active_calories", "daily_activity", "Active calories", "kcal", "higher_better", _f("active_calories")),
    MetricDef("average_met_minutes", "daily_activity", "Avg MET minutes", "", "higher_better", _f("average_met_minutes")),
    MetricDef("sedentary_time", "daily_activity", "Sedentary time", "s", "lower_better", _f("sedentary_time")),
    MetricDef("spo2_avg", "daily_spo2", "Average SpO2", "%", "higher_better", lambda r: _nested_avg(r, "spo2_percentage")),
    MetricDef("breathing_disturbance_index", "daily_spo2", "Breathing disturbance", "", "lower_better", _f("breathing_disturbance_index")),
    MetricDef("vascular_age", "daily_cardiovascular_age", "Vascular age", "yr", "lower_better", _f("vascular_age")),
    MetricDef("vo2_max", "vO2_max", "VO2 max", "", "higher_better", _f("vo2_max")),
]


def build_frame(storage: Storage) -> pd.DataFrame:
    records: dict[str, list[dict[str, Any]]] = {}
    rows: list[dict[str, Any]] = []
    for m in METRICS:
        if m.collection not in records:
            records[m.collection] = storage.read(m.collection)
        for rec in records[m.collection]:
            day = rec.get("day")
            if not day:
                continue
            val = m.extract(rec)
            if val is None:
                continue
            rows.append({"day": day, "metric": m.key, "value": val})
    if not rows:
        return pd.DataFrame(
            {
                "day": pd.Series(dtype="datetime64[ns]"),
                "metric": pd.Series(dtype=str),
                "value": pd.Series(dtype=float),
            }
        )
    df = pd.DataFrame(rows)
    df["day"] = pd.to_datetime(df["day"])
    df = df.groupby(["day", "metric"])["value"].mean().reset_index()
    return df


def metric_labels() -> dict[str, str]:
    return {m.key: m.label for m in METRICS}

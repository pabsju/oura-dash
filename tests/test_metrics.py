import pandas as pd

from oura_dash.metrics import METRICS, build_frame, metric_labels
from oura_dash.storage import Storage


def _keys():
    return {m.key for m in METRICS}


def test_registry_covers_key_metrics():
    for k in {"stress_high", "recovery_high", "average_hrv", "sleep_score",
              "readiness_score", "steps", "spo2_avg", "vascular_age", "vo2_max"}:
        assert k in _keys()


def test_nested_spo2_extractor():
    m = next(m for m in METRICS if m.key == "spo2_avg")
    assert m.extract({"spo2_percentage": {"average": 96.5}}) == 96.5
    assert m.extract({"spo2_percentage": None}) is None
    assert m.extract({}) is None


def test_build_frame_long_format_and_daily_average():
    with Storage(":memory:") as st:
        st.init_schema()
        st.upsert("daily_stress", [{"id": "a", "day": "2026-06-20", "stress_high": 300}])
        # two sleep records same day -> averaged
        st.upsert("sleep", [
            {"id": "s1", "day": "2026-06-20", "average_hrv": 40, "type": "long_sleep"},
            {"id": "s2", "day": "2026-06-20", "average_hrv": 60, "type": "long_sleep"},
        ])
        df = build_frame(st)
    assert set(df.columns) == {"day", "metric", "value"}
    hrv = df[(df.metric == "average_hrv") & (df.day == pd.Timestamp("2026-06-20"))]
    assert hrv["value"].iloc[0] == 50.0
    stress = df[df.metric == "stress_high"]
    assert stress["value"].iloc[0] == 300.0


def test_metric_labels_map():
    labels = metric_labels()
    assert labels["average_hrv"]  # non-empty label exists


def test_empty_frame_has_typed_columns():
    with Storage(":memory:") as st:
        st.init_schema()
        df = build_frame(st)
    assert pd.api.types.is_datetime64_any_dtype(df["day"])
    assert pd.api.types.is_float_dtype(df["value"])


def test_bool_values_rejected():
    m = next(m for m in METRICS if m.key == "stress_high")
    assert m.extract({"stress_high": True}) is None


def test_naps_excluded_from_sleep_metrics():
    with Storage(":memory:") as st:
        st.init_schema()
        st.upsert("sleep", [
            {"id": "s1", "day": "2026-06-20", "average_hrv": 50, "type": "long_sleep"},
            {"id": "s2", "day": "2026-06-20", "average_hrv": 90, "type": "late_nap"},
        ])
        df = build_frame(st)
    hrv = df[(df.metric == "average_hrv") & (df.day == pd.Timestamp("2026-06-20"))]
    assert hrv["value"].iloc[0] == 50.0

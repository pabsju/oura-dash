from datetime import date

import pandas as pd
import plotly.graph_objects as go

from oura_dash.metrics import build_frame, metric_labels
from oura_dash.stats import BenchmarkReport


def latest_values(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame(columns=["metric", "day", "value"])
    idx = frame.groupby("metric")["day"].idxmax()
    return frame.loc[idx, ["metric", "day", "value"]].sort_values("metric").reset_index(drop=True)


def trend_figure(
    frame: pd.DataFrame, metric_key: str, window_start: date, window_end: date, label: str
) -> go.Figure:
    sub = frame[frame.metric == metric_key].sort_values("day")
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sub["day"], y=sub["value"], mode="lines+markers", name=label))
    fig.add_vrect(
        x0=pd.Timestamp(window_start), x1=pd.Timestamp(window_end),
        fillcolor="LightSalmon", opacity=0.25, line_width=0, annotation_text="window",
    )
    fig.update_layout(title=label, xaxis_title="day", yaxis_title=label, height=350)
    return fig


_RESULTS_TABLE_COLUMNS = [
    "metric", "label", "n_baseline", "n_window", "median_baseline", "median_window",
    "cliffs_delta", "ci", "p_value", "q_value",
]


def results_table(report: BenchmarkReport) -> pd.DataFrame:
    labels = metric_labels()
    if not report.results:
        return pd.DataFrame(columns=_RESULTS_TABLE_COLUMNS)
    return pd.DataFrame([
        {
            "metric": r.metric, "label": labels.get(r.metric, r.metric),
            "n_baseline": r.n_baseline, "n_window": r.n_window,
            "median_baseline": r.median_baseline, "median_window": r.median_window,
            "cliffs_delta": r.cliffs_delta, "ci": f"[{r.ci_low:.2f}, {r.ci_high:.2f}]",
            "p_value": r.p_value, "q_value": r.q_value,
        }
        for r in report.results
    ])


def render(storage, settings) -> None:  # pragma: no cover - Streamlit UI
    import streamlit as st

    from oura_dash.stats import benchmark

    frame = build_frame(storage)
    labels = metric_labels()
    st.title("Oura daily metrics")
    overview, trends, bench = st.tabs(["Overview", "Trends", "Benchmark"])

    with overview:
        st.subheader("Latest values")
        st.dataframe(latest_values(frame), width="stretch")

    with trends:
        if frame.empty:
            st.info("No data yet. Run `oura-dash backfill`.")
        else:
            for key in sorted(frame["metric"].unique()):
                st.plotly_chart(
                    trend_figure(frame, key, settings.window_start, settings.window_end,
                                 labels.get(key, key)),
                    key=f"trend_{key}",
                    width="stretch",
                )

    with bench:
        report = benchmark(frame, settings)
        if report.interim:
            st.warning("Interim: window not yet complete; results are provisional.")
        st.dataframe(results_table(report), width="stretch")
        st.caption("Daily series are autocorrelated; p-values are approximate.")


def _main() -> None:  # pragma: no cover - entry path
    from oura_dash.config import Settings
    from oura_dash.storage import Storage

    settings = Settings()
    with Storage(settings.db_path) as storage:
        render(storage, settings)


if __name__ == "__main__":  # pragma: no cover - only runs under `streamlit run`
    _main()

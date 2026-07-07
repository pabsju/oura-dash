import subprocess
import sys
from datetime import date
from pathlib import Path

import pydantic
import typer

from oura_dash import metrics as metrics_mod
from oura_dash import stats as stats_mod
from oura_dash import sync as sync_mod
from oura_dash.client import OuraClient
from oura_dash.config import Settings
from oura_dash.storage import Storage

app = typer.Typer(help="Oura daily-metrics dashboard and benchmark.")


def _make_settings() -> Settings:
    try:
        return Settings()
    except pydantic.ValidationError as exc:
        if any(err.get("loc") == ("token",) for err in exc.errors()):
            typer.echo(
                "OURA_TOKEN not set. Copy .env.example to .env and add your "
                "Personal Access Token.",
                err=True,
            )
            raise typer.Exit(code=1) from exc
        raise


def _make_client(settings: Settings) -> OuraClient:
    return OuraClient(settings.token, base_url=settings.base_url)


@app.command()
def version() -> None:
    """Print version."""
    from oura_dash import __version__

    typer.echo(__version__)


@app.command()
def backfill() -> None:
    """Fetch all historical data for every collection."""
    settings = _make_settings()
    client = _make_client(settings)
    with Storage(settings.db_path) as storage:
        counts = sync_mod.backfill(client, storage, settings)
    for name, n in counts.items():
        typer.echo(f"{name}: {n}")


@app.command()
def sync() -> None:
    """Incrementally fetch new data since last stored day."""
    settings = _make_settings()
    client = _make_client(settings)
    with Storage(settings.db_path) as storage:
        counts = sync_mod.incremental(client, storage, settings)
    for name, n in counts.items():
        typer.echo(f"{name}: {n}")


def _print_report(report: stats_mod.BenchmarkReport) -> None:
    typer.echo(f"{'metric':<28}{'n_base':>7}{'n_win':>7}{'med_base':>10}{'med_win':>10}{'delta':>8}{'p':>9}{'q':>9}")
    for r in report.results:
        typer.echo(
            f"{r.metric:<28}{r.n_baseline:>7}{r.n_window:>7}"
            f"{r.median_baseline:>10.2f}{r.median_window:>10.2f}"
            f"{r.cliffs_delta:>8.2f}{r.p_value:>9.4f}{r.q_value:>9.4f}"
        )


@app.command()
def stats(
    window_start: str = typer.Option(None, help="YYYY-MM-DD override"),
    window_end: str = typer.Option(None, help="YYYY-MM-DD override"),
    baseline_start: str = typer.Option(None, help="YYYY-MM-DD override for bounded baseline"),
) -> None:
    """Benchmark the window vs all history and vs a bounded baseline window."""
    settings = _make_settings()
    if window_start:
        settings.window_start = date.fromisoformat(window_start)
    if window_end:
        settings.window_end = date.fromisoformat(window_end)
    if baseline_start:
        settings.baseline_start = date.fromisoformat(baseline_start)
    with Storage(settings.db_path) as storage:
        frame = metrics_mod.build_frame(storage)
    report_all = stats_mod.benchmark(frame, settings)
    report_bounded = stats_mod.benchmark(frame, settings, baseline_start=settings.baseline_start)
    if report_all.interim:
        typer.echo("** INTERIM: window not yet complete; results are provisional. **")
    typer.echo("== Window vs all history ==")
    _print_report(report_all)
    typer.echo(f"\n== Window vs baseline window ({settings.baseline_start} → {settings.window_start}) ==")
    _print_report(report_bounded)
    typer.echo("\nNote: daily series are autocorrelated; p-values are approximate.")


def _run_streamlit(args: list[str]) -> object:
    return subprocess.run(args)


@app.command()
def serve() -> None:
    """Launch the Streamlit dashboard."""
    app_path = str(Path(__file__).with_name("app.py"))
    _run_streamlit([sys.executable, "-m", "streamlit", "run", app_path])

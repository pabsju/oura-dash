import typer

app = typer.Typer(help="Oura daily-metrics dashboard and benchmark.")


@app.command()
def version() -> None:
    """Print version."""
    from oura_dash import __version__

    typer.echo(__version__)

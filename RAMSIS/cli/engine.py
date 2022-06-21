import typer
from RAMSIS.core.engine.engine import Engine

app = typer.Typer()

@app.command()
def run(forecast_id: int):
    typer.echo(f"Running ramsis engine with {forecast_id}")
    engine = Engine()
    engine.run(forecast_id)

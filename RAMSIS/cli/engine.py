import typer
from ramsis.datamodel import Forecast
from RAMSIS.db import store
from RAMSIS.core.engine.engine import Engine
from RAMSIS.utils import reset_forecast

app = typer.Typer()

# To be removed once engine migrated to prefect.


@app.command()
def run(forecast_id: int,
        force: bool = typer.Option(
            False, help="Force the forecast to run again, "
                        "even if completed.")):
    session = store.session
    forecast = session.query(Forecast).filter(
        Forecast.id == forecast_id).one_or_none()
    if not forecast:
        typer.echo("The forecast id does not exist")
        raise typer.Exit()
    else:
        typer.echo(f"forecast found: {forecast}")
    if force:
        _ = reset_forecast(forecast)
    session.commit()
    typer.echo(f"Running ramsis engine with {forecast_id}")
    engine = Engine()
    engine.run(forecast_id)

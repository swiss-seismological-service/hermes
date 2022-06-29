import typer
from datetime import timedelta
from ramsis.datamodel import Forecast, EStatus
from RAMSIS.db import store
from RAMSIS.flows.register import \
    get_client
from RAMSIS.cli.utils import schedule_forecast, get_idempotency_id, \
    reset_forecast


app = typer.Typer()


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
        forecast = reset_forecast(forecast)
    session.commit()

    if forecast.status.state != EStatus.COMPLETE:
        client = get_client()
        idempotency_id = get_idempotency_id()
        schedule_forecast(forecast, client, idempotency_id=idempotency_id)
    else:
        typer.echo("Forecast is already complete.")


@app.command()
def clone(forecast_id: int,
          interval: int = typer.Argument(
              ..., help="Interval in seconds between forecasts."),
          clone_number: int = typer.Argument(
              ..., help="Number of forecast clones to create."),
          ):

    session = store.session
    forecast = session.query(Forecast).filter(
        Forecast.id == forecast_id).one_or_none()
    if not forecast:
        typer.echo("The forecast id does not exist")
        raise typer.Exit()

    new_forecasts = []

    typer.echo(f"Forecasts being cloned from id: {forecast_id} "
               f"which has starttime: {forecast.starttime}")
    for i in range(1, clone_number + 1):
        cloned = forecast.clone(with_results=False)
        cloned.starttime = (
            forecast.starttime + timedelta(
                seconds=interval * i))
        if cloned.starttime >= cloned.endtime:
            typer.echo("Some forecast startimes exceed the endtime, "
                       "so they will not be created.")
            break

        cloned.project_id = forecast.project_id
        cloned = reset_forecast(cloned)
        session.add(cloned)
        new_forecasts.append(cloned)

    session.commit()
    for new_forecast in new_forecasts:
        new_forecast.name = f"Forecast {new_forecast.id}"
    session.commit()
    for forecast in new_forecasts:
        typer.echo(f"New forecast initialized with id: {forecast.id} "
                   f"and starttime: {forecast.starttime}")
    typer.echo(f"{len(new_forecasts)} Forecasts added successfully.")


@app.command()
def delete(forecast_id: int):
    session = store.session
    forecast_queried = session.query(Forecast).filter(
        Forecast.id == forecast_id).one_or_none()
    if not forecast_queried:
        typer.echo("The forecast does not exist")
        raise typer.Exit()
    delete = typer.confirm("Are you sure you want to delete the  "
                           f"forecast with id: {forecast_id}")
    if not delete:
        typer.echo("Not deleting")
        raise typer.Abort()

    session.query(Forecast).filter(
        Forecast.id == forecast_id).delete()
    session.commit()
    typer.echo("Finished deleting forecast")

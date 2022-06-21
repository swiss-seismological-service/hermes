import typer
from datetime import timedelta
from typing import List
from ramsis.datamodel import Forecast, EStatus
from RAMSIS.db import store
from RAMSIS.flows.register import \
    get_client
from RAMSIS.cli.utils import schedule_forecast


app = typer.Typer()


@app.command()
def run(forecast_id: int):
    session = store.session
    forecast = session.query(Forecast).filter(Forecast.id == forecast_id).one_or_none()
    if not forecast:
        typer.echo("The forecast id does not exist")
        raise typer.Exit()

    if forecast.status.state != EStatus.COMPLETE:
        client = get_client()
        schedule_forecast(forecast, client)



@app.command()
def clone(forecast_id: int,
          interval: int = typer.Argument(..., help="Interval in seconds between forecasts."),
          clone_number: int = typer.Argument(..., help="Number of forecast clones to create."),
          ):

    session = store.session
    forecast = session.query(Forecast).filter(Forecast.id == forecast_id).one_or_none()
    if not forecast:
        typer.echo("The forecast id does not exist")
        raise typer.Exit()

    new_forecasts = []

    typer.echo(f"Forecasts being cloned from id: {forecast_id} which has starttime: {forecast.starttime}")
    for i in range(1, clone_number + 1):
        cloned = forecast.clone(with_results=False)
        cloned.starttime = (
            forecast.starttime + timedelta(
            seconds=interval * i))
        if cloned.starttime >= cloned.endtime:
            typer.echo("Some forecast startimes exceed the endtime, so they will not be created.")
            break
        else:
            session.add(cloned)
            new_forecasts.append(cloned)
    session.commit()
    for forecast in new_forecasts: 
        typer.echo(f"New forecast initialized with id: {forecast.id} and starttime: {forecast.starttime}")
    typer.echo(f"{len(new_forecasts)} Forecasts added successfully.")


@app.command()
def delete(forecast_ids: List[int]):
    forecast_ids = list(forecast_ids)
    typer.echo(f"{forecast_ids}, {type(forecast_ids)}")
    session = store.session
    forecasts_queried = session.query(Forecast).filter(Forecast.id.in_(forecast_ids)).all()
    list_ids = [f.id for f in forecasts_queried]
    if not forecasts_queried:
        typer.echo("The forecast ids do not exist")
        raise typer.Exit()
    delete = typer.confirm(f"Are you sure you want to delete the following forecasts: {*list_ids,}")
    if not delete:
        typer.echo("Not deleting")
        raise typer.Abort()

    # https://docs.sqlalchemy.org/en/14/orm/session_basics.html#update-and-delete-with-arbitrary-where-clause
    # Think about execution_options
    #forecasts_for_deletion = session.query(Forecast).filter(Forecast.id.in_(forecast_ids)).all()
    #forecasts_deleted = session.query(Forecast).filter(Forecast.id.in_(forecast_ids)).delete()
    session.remove()
    for forecast in forecasts_queried:
        print(f"forecast {forecast.id}")
        forecast_deleted = session.query(Forecast).filter(
            Forecast.id == forecast.id).delete()
    print(f" after forecast {forecast.id}")
    #for forecast in forecasts_queried:
    #    typer.echo("Deleting forecast {forecast.id}")
    session.commit()
    typer.echo("Finished deleting forecasts")

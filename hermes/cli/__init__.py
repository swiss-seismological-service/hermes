import typer

from hermes.cli.forecast import app as forecast
from hermes.cli.forecastseries import app as forecastseries
from hermes.cli.injectionplan import app as injectionplan
from hermes.cli.model import app as model
from hermes.cli.project import app as project
from hermes.cli.schedule import app as schedule
from hermes.repositories.database import _create_tables, _drop_tables

app = typer.Typer(pretty_exceptions_enable=False)
app.add_typer(project, name="projects")
app.add_typer(forecastseries, name="forecastseries")
app.add_typer(model, name="models")
app.add_typer(forecast, name="forecasts")
app.add_typer(schedule, name="schedules")
app.add_typer(injectionplan, name="injectionplans")


@app.command()
def create_tables():
    _create_tables()


@app.command()
def drop_tables():
    _drop_tables()

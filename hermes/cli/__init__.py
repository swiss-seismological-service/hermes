import typer

from hermes.cli.forecastseries import app as forecastseries
from hermes.cli.project import app as project
from hermes.db import _create_tables, _drop_tables

app = typer.Typer()
app.add_typer(project, name="project")
app.add_typer(forecastseries, name="forecastseries")


@app.command()
def create_tables():
    _create_tables()


@app.command()
def drop_tables():
    _drop_tables()

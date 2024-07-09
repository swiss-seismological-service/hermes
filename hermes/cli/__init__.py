import asyncio

import typer

from hermes.cli.forecast import app as forecast
from hermes.cli.project import app as project
from hermes.db import _create_tables, _drop_tables

app = typer.Typer()
app.add_typer(project, name="project")
app.add_typer(forecast, name="forecast")


@app.command()
def create_tables():
    _create_tables()


@app.command()
def drop_tables():
    _drop_tables()

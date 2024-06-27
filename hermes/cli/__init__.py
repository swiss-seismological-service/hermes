import asyncio

import typer

from hermes.cli.forecast import app as forecast
from hermes.cli.project import app as project
from hermes.db import _create_db, _drop_db

app = typer.Typer()
app.add_typer(project, name="project")
app.add_typer(forecast, name="forecast")


@app.command()
def create_db():
    asyncio.run(_create_db())


@app.command()
def drop_tables():
    asyncio.run(_drop_db())

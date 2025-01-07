import os

import typer

from alembic import script
from alembic.config import Config
from alembic.runtime import migration
from hermes.repositories.database import _check_tables_exist, engine

ALEMBIC_CFG = Config(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                  '../../../alembic.ini'))


def check_current_head(alembic_cfg) -> bool:
    directory = script.ScriptDirectory.from_config(alembic_cfg)
    with engine.begin() as connection:
        context = migration.MigrationContext.configure(connection)
        return set(context.get_current_heads()) == set(directory.get_heads())


def check_db():
    if not _check_tables_exist():
        typer.echo("Please initialize the database first.")
        raise typer.Abort()
    if not check_current_head(ALEMBIC_CFG):
        typer.echo("Please upgrade the database first.")
        raise typer.Abort()

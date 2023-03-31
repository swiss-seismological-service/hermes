import typer
from RAMSIS.db import db_url, session_handler, init_db
from ramsis.datamodel import ModelConfig
import json
from ramsis.io.configuration import ModelConfigurationSchema
from pathlib import Path

from sqlalchemy import select


app = typer.Typer()


@app.command()
def delete(
        model_name: str,
        force: bool = typer.Option(
            False, help="Force the deletes without asking")):
    with session_handler(db_url) as session:
        model_config = session.execute(
            select(ModelConfig).filter_by(
                name=model_name)).\
            scalar_one_or_none()
        if not model_config:
            typer.echo("Model does not exist")
            raise typer.Exit()
        if model_config.runs:
            typer.echo("Model config is associated with model runs, "
                       "cannot delete. You can disable instead.")
            raise typer.Exit()
            if not force:
                delete = typer.confirm("Are you sure you want to delete the  "
                                       f"model with name: {model_name}?")
                if not delete:
                    typer.echo("Not deleting")
                    raise typer.Abort()
        session.delete(model_config)
        session.commit()


@app.command()
def load(
        model_config: Path = typer.Option(
        ...,
        exists=True, readable=True, help=(
            "Path to model config containing Seismicity Model config"))):

    success = init_db(db_url)

    if success:
        pass
    else:
        typer.echo(f"Error, db could not be initialized: {success}")
        raise typer.Exit()
    with session_handler(db_url) as session:
        with open(model_config, "r") as model_read:
            config_dict = json.load(model_read)

        for config in config_dict["model_configs"]:
            new_model_config = ModelConfigurationSchema().load(config)

            existing_config = session.execute(
                select(ModelConfig).filter_by(
                    name=new_model_config.name)).\
                scalar_one_or_none()
            if existing_config:
                typer.echo(f"Model config exists for {new_model_config.name}.")
                # Check if there are already completed forecasts
                # associated before allowing modification.
                if existing_config.runs:
                    typer.echo("Model runs already exist for this config"
                               " Please upload the config with a new name.")
                    typer.Exit(code=1)
                typer.echo(" Will update existing config.")
                new_model_config.id = existing_config.id
            else:
                typer.echo("Model config is being added for "
                           f"{new_model_config.name}")
            updated_model_config = session.merge(new_model_config)

            typer.echo("A model has been configured with the name: "
                       f"{updated_model_config}")
        session.commit()

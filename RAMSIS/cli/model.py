import typer
from rich import print
from rich.table import Table
from marshmallow import EXCLUDE
from RAMSIS.db import db_url, session_handler, init_db
from ramsis.datamodel import ModelConfig
import json
from ramsis.io.configuration import ModelConfigurationSchema
from pathlib import Path

from sqlalchemy import select


app = typer.Typer()


@app.command()
def ls(help="Outputs list of models"):
    with session_handler(db_url) as session:
        model_configs = session.execute(
            select(ModelConfig)).scalars().all()
        for model in model_configs:
            table = Table(show_footer=False,
                          title=f"Model Config {model.name}",
                          title_justify="left")
            table.add_column("attribute")
            table.add_column("value")
            for attr in ModelConfig.__table__.columns:
                table.add_row(str(attr.name), str(getattr(model, attr.name)))

            print(table)


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
            print("Model does not exist")
            raise typer.Exit()
        if model_config.runs:
            print("Model config is associated with model runs, "
                  "cannot delete. You can disable instead.")
            raise typer.Exit()
            if not force:
                delete = typer.confirm("Are you sure you want to delete the  "
                                       f"model with name: {model_name}?")
                if not delete:
                    print("Not deleting")
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
        print(f"Error, db could not be initialized: {success}")
        raise typer.Exit()
    with session_handler(db_url) as session:
        with open(model_config, "r") as model_read:
            config_dict = json.load(model_read)

        for config in config_dict["model_configs"]:
            existing_config = session.execute(
                select(ModelConfig).filter_by(
                    name=config["name"])).\
                scalar_one_or_none()

            if existing_config:
                print(f"Model config exists for {existing_config.name}.")
                # Check if there are already completed forecasts
                # associated before allowing modification.
                print(existing_config.runs, "existing runs")
                if existing_config.runs:
                    session.rollback()
                    print("Model runs already exist for this config"
                          " Please upload the config with a new name.")
                    raise typer.Exit(code=1)
                print("deleting existing config")
                session.delete(existing_config)
                new_model_config = ModelConfigurationSchema(
                    unknown=EXCLUDE, context={"session": session}).load(config)
                new_model_config.id = existing_config.id
            else:
                new_model_config = ModelConfigurationSchema(
                    unknown=EXCLUDE, context={"session": session}).load(config)
                print("Model config is being added for "
                      f"{new_model_config.name}")

            session.add(new_model_config)
            session.commit()
            print("A model has been configured with the name: "
                  f"{new_model_config.name}, id: {new_model_config.id}")

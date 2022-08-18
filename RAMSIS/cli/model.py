import typer
from RAMSIS.db import store
import json
from ramsis.datamodel import SeismicityModel
from pathlib import Path
from sqlalchemy import select


app = typer.Typer()


def create_sm(store, sm_model_config):

    sm = SeismicityModel(
        name=sm_model_config["MODEL_NAME"],
        config=sm_model_config["CONFIG"],
        sfmwid=sm_model_config["SFMWID"],
        enabled=sm_model_config["ENABLED"],
        url=sm_model_config["URL"])

    typer.echo(f"Creating new seismicity model: {sm}")
    store.add(sm)


def update_sm(store, existing_sm, sm_model_config):
    existing_sm.name = sm_model_config["MODEL_NAME"]
    existing_sm.config = sm_model_config["CONFIG"]
    existing_sm.sfmwid = sm_model_config["SFMWID"]
    existing_sm.enabled = sm_model_config["ENABLED"]
    existing_sm.url = sm_model_config["URL"]

    typer.echo(f"Updating existing seismicity model: {existing_sm}")
    store.add(existing_sm)


@app.command()
def configure(
        model_config: Path = typer.Option(
        ...,
        exists=True,
        readable=True)):

    success = store.init_db()

    if success:
        pass
    else:
        typer.echo(f"Error, db could not be initialized: {success}")
        raise typer.Exit()
    session = store.session
    with open(model_config, "r") as model_read:
        config = json.load(model_read)
    seismicity_config = config["SEISMICITY_MODELS"]

    for sm_model_config in seismicity_config:
        existing_sm_model = session.execute(
            select(SeismicityModel).filter_by(
                name=sm_model_config["MODEL_NAME"])).\
            scalar_one_or_none()
        if not existing_sm_model:
            create_sm(store, sm_model_config)
        else:
            update_sm(store, existing_sm_model, sm_model_config)
    store.save()
    store.close()


#@app.command()
#def disable(model_: Path = typer.Option(
#also enable - should create and remove model runs that are
# associated with the model.

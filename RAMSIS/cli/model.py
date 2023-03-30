import typer
from RAMSIS.db import db_url, session_handler, init_db
import json
from ramsis.datamodel import SeismicityModel, HazardModel
from pathlib import Path
from sqlalchemy import select


app = typer.Typer()


def create_sm(session, sm_model_config, hazardsourcemodeltemplate=None):
    sm = SeismicityModel(
        name=sm_model_config["MODEL_NAME"],
        config=sm_model_config["CONFIG"],
        sfmwid=sm_model_config["SFMWID"],
        enabled=sm_model_config["ENABLED"],
        url=sm_model_config["URL"])

    if hazardsourcemodeltemplate:
        sm.hazardsourcemodeltemplate = hazardsourcemodeltemplate
    if "HAZARD_WEIGHT" in sm_model_config.keys():
        sm.hazardweight = sm_model_config["HAZARD_WEIGHT"]
    typer.echo(f"Creating new seismicity model: {sm}")
    session.add(sm)


def update_sm(session, existing_sm, sm_model_config,
              hazardsourcemodeltemplate=None):
    existing_sm.name = sm_model_config["MODEL_CONFIG_NAME"]
    existing_sm.description = sm_model_config["MODEL_CONFIG_NAME"]
    existing_sm.config = sm_model_config["CONFIG"]
    existing_sm.sfmwid = sm_model_config["SFMWID"]
    existing_sm.enabled = sm_model_config["ENABLED"]
    existing_sm.url = sm_model_config["URL"]
    typer.echo(f"Updating existing seismicity model: {existing_sm}")
    session.add(existing_sm)


@app.command()
def update:(
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
            configs = json.load(model_read)

        for config in configs:
            existing_sm_model = session.execute(
                select(ModelConfig).filter_by(
                    name=config["MODEL_CONFIG_NAME"])).\
                scalar_one_or_none()
            if not existing_sm_model:
                create_sm(session, config)
            else:
                update_sm(session, existing_sm_model, config)
        session.commit()


@app.command()
def add_hazard(
        model_config: Path = typer.Option(
        ...,
        exists=True,
        readable=True,
        help="Path to model config containing Hazard Model config"),
        gsimlogictree_path: Path = typer.Option(
        ...,
        exists=True,
        readable=True,
        help="Path to gsim logic tree file for running with OpenQuake")):

    success = init_db(db_url)

    if success:
        pass
    else:
        typer.echo(f"Error, db could not be initialized: {success}")
        raise typer.Exit()
    with session_handler(db_url) as session:
        with open(model_config, "r") as model_read:
            config = json.load(model_read)
        with open(gsimlogictree_path, "r") as gsim_read:
            gsimlogictree = gsim_read.read()

        existing_haz_model = session.execute(
            select(HazardModel).filter_by(
                name=config["MODEL_NAME"])).\
            scalar_one_or_none()
        if not existing_haz_model:
            create_hm(session, config, gsimlogictree)
        else:
            update_hm(session, existing_haz_model, config, gsimlogictree)
        session.commit()

# @app.command()
# def disable(model_: Path = typer.Option(
# also enable - should create and remove model runs that are
#  associated with the model.

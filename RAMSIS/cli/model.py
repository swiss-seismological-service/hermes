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
    existing_sm.name = sm_model_config["MODEL_NAME"]
    existing_sm.config = sm_model_config["CONFIG"]
    existing_sm.sfmwid = sm_model_config["SFMWID"]
    existing_sm.enabled = sm_model_config["ENABLED"]
    existing_sm.url = sm_model_config["URL"]
    if "HAZARD_WEIGHT" in sm_model_config.keys():
        existing_sm.hazardweight = sm_model_config["HAZARD_WEIGHT"]
    if hazardsourcemodeltemplate:
        existing_sm.hazardsourcemodeltemplate = hazardsourcemodeltemplate

    typer.echo(f"Updating existing seismicity model: {existing_sm}")
    session.add(existing_sm)


def create_hm(session, model_config, gsimlogictree):

    hm = HazardModel(
        name=model_config["MODEL_NAME"],
        config=model_config["CONFIG"],
        jobconfig=model_config["JOBCONFIG"],
        enabled=model_config["ENABLED"],
        url=model_config["URL"],
        gsimlogictree=gsimlogictree)

    typer.echo(f"Creating new hazard model: {hm}")
    session.add(hm)


def update_hm(session, existing_model, model_config, gsimlogictree):
    existing_model.name = model_config["MODEL_NAME"]
    existing_model.config = model_config["CONFIG"]
    existing_model.jobconfig = model_config["JOBCONFIG"]
    existing_model.enabled = model_config["ENABLED"]
    existing_model.url = model_config["URL"]
    existing_model.gsimlogictree = gsimlogictree

    typer.echo(f"Updating existing hazard model: {existing_model}")
    session.add(existing_model)


@app.command()
def configure(
        model_config: Path = typer.Option(
        ...,
        exists=True,
        readable=True)):

    success = init_db(db_url)

    if success:
        pass
    else:
        typer.echo(f"Error, db could not be initialized: {success}")
        raise typer.Exit()
    with session_handler(db_url) as session:
        with open(model_config, "r") as model_read:
            config = json.load(model_read)
        seismicity_config = config["SEISMICITY_MODELS"]

        for sm_model_config in seismicity_config:
            existing_sm_model = session.execute(
                select(SeismicityModel).filter_by(
                    name=sm_model_config["MODEL_NAME"])).\
                scalar_one_or_none()
            if not existing_sm_model:
                create_sm(session, sm_model_config)
            else:
                update_sm(session, existing_sm_model, sm_model_config)
        session.commit()


@app.command()
def add_seismicity(
        model_config: Path = typer.Option(
        ...,
        exists=True, readable=True, help=(
            "Path to model config containing Seismicity Model config")),
        hazardsourcemodeltemplate_path: Path = typer.Option(
        None, exists=True, readable=True, help=(
            "Path to a source model xml template. Please see tests for "
            "examples"))):

    success = init_db(db_url)

    if success:
        pass
    else:
        typer.echo(f"Error, db could not be initialized: {success}")
        raise typer.Exit()
    with session_handler(db_url) as session:
        with open(model_config, "r") as model_read:
            config = json.load(model_read)
        with open(hazardsourcemodeltemplate_path, "r") as sourcemodel_read:
            hazardsourcemodeltemplate = sourcemodel_read.read()

        existing_sm_model = session.execute(
            select(SeismicityModel).filter_by(
                name=config["MODEL_NAME"])).\
            scalar_one_or_none()
        if not existing_sm_model:
            create_sm(session, config,
                      hazardsourcemodeltemplate=hazardsourcemodeltemplate)
        else:
            update_sm(session, existing_sm_model, config,
                      hazardsourcemodeltemplate=hazardsourcemodeltemplate)
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

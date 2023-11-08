import typer
from rich import print
from rich.table import Table
import json
from sqlalchemy import select
from ramsis.datamodel import Project
from pathlib import Path
from RAMSIS.db import db_url, session_handler, init_db
from ramsis.io.configuration import ProjectConfigurationSchema


app = typer.Typer()


@app.command()
def create(
        config: Path = typer.Option(
        ...,
        exists=True,
        readable=True,
        help="Path to json project config."),
        catalog_data: typer.FileText = typer.Option(
        None, help="Path of file containing the "
        "catalog for forecasts without using fdsnws, e.g. for replays."),
        well_data: typer.FileText = typer.Option(
        None, help="Path of file containing inj data for replays ")):

    success = init_db(db_url)

    if success:
        pass
    else:
        print(f"Error, db could not be initialized: {success}")
        raise typer.Exit()

    with session_handler(db_url) as session:

        with open(config, "r") as project_json:
            project_config_dict = json.load(project_json)
            project_config_list = project_config_dict['project_configs']

        new_projects = []
        for project_config in project_config_list:
            matching_project = session.execute(
                select(Project.name, Project.id).where(
                    Project.name == project_config["name"])).first()
            if matching_project:
                raise Exception(
                    "Project name: "
                    f"{matching_project.name} already exists "
                    f"with id: {matching_project.id}")

            project = ProjectConfigurationSchema().load(project_config)
            session.add(project)
            new_projects.append(project)

            if catalog_data:
                project.seismiccatalog = catalog_data.read().encode(
                    encoding='utf-8')
            if well_data:
                project.injectionwell = json.dumps(
                    [json.loads(well_data.read())], ensure_ascii=False).encode(
                    encoding='utf-8')
            session.commit()

        for project in new_projects:
            print(f"created project {project.name} "
                  f"with id: {project.id}")


@app.command()
def update(
        project_id: int,
        config: Path = typer.Option(
        ...,
        exists=True,
        readable=True,
        help="Path to json project config.")):

    with session_handler(db_url) as session:

        with open(config, "r") as project_json:
            project_config_list = json.load(project_json)['project_configs']

        assert len(project_config_list) == 1
        project_config = project_config_list[0]
        project = session.execute(
            select(Project).filter_by(id=project_id)).scalar_one_or_none()
        if not project:
            print(f"Project id {project_id} does not exist")
            raise typer.Exit()

        updated_project = ProjectConfigurationSchema(project_config)
        updated_project.id = project.id
        session.merge()
        session.commit()
        print(f"updated project {project.name} "
              f"with id: {project.id}")


@app.command()
def ls(help="Outputs list of projects"):
    with session_handler(db_url) as session:
        projects = session.execute(
            select(Project)).scalars().all()
        for project in projects:
            table = Table(show_footer=False,
                          title=f"Project {project.name}",
                          title_justify="left")
            table.add_column("attribute")
            table.add_column("value")
            for attr in Project.__table__.columns:
                table.add_row(str(attr.name), str(getattr(project, attr.name)))

            print(table)


@app.command()
def delete(project_id: int):
    with session_handler(db_url) as session:
        project = session.execute(
            select(Project).filter_by(id=project_id)).scalar_one_or_none()
        if not project:
            print("The project does not exist")
            raise typer.Exit()
        delete = typer.confirm("Are you sure you want to delete the  "
                               f"project with id: {project_id}")
        if not delete:
            print("Not deleting")
            raise typer.Abort()

        session.delete(project)
        session.commit()
        print("Finished deleting project")

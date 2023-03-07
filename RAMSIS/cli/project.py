import typer
import json
from sqlalchemy import select
from ramsis.datamodel import Project
from pathlib import Path
from RAMSIS.db import db_url, session_handler, init_db
from RAMSIS.cli.utils import create_project, update_project

app = typer.Typer()


@app.command()
def create(
        config: Path = typer.Option(
        ...,
        exists=True,
        readable=True,
        help="Path to json project config.")):

    success = init_db(db_url)

    if success:
        pass
    else:
        typer.echo(f"Error, db could not be initialized: {success}")
        raise typer.Exit()

    with session_handler(db_url) as session:

        with open(config, "r") as project_json:
            project_config_list = json.load(project_json)['PROJECTS']

        new_projects = []
        for project_config in project_config_list:
            matching_project = session.execute(
                select(Project.name, Project.id).where(
                    Project.name == project_config["PROJECT_NAME"])).first()
            if matching_project:
                raise Exception(
                    "Project name: "
                    f"{matching_project.name} already exists "
                    f"with id: {matching_project.id}")

            project = create_project(project_config)
            session.add(project)
            new_projects.append(project)
            session.commit()
        for project in new_projects:
            typer.echo(f"created project {project.name} "
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
            project_config_list = json.load(project_json)['PROJECTS']

        assert len(project_config_list) == 1
        project_config = project_config_list[0]
        project = session.execute(
            select(Project).filter_by(id=project_id)).scalar_one_or_none()
        if not project:
            typer.echo(f"Project id {project_id} does not exist")
            raise typer.Exit()

        project = update_project(project, project_config)
        session.commit()
        typer.echo(f"updated project {project.name} "
                   f"with id: {project.id}")


@app.command()
def delete(project_id: int):
    with session_handler(db_url) as session:
        project = session.execute(
            select(Project).filter_by(id=project_id)).scalar_one_or_none()
        if not project:
            typer.echo("The project does not exist")
            raise typer.Exit()
        delete = typer.confirm("Are you sure you want to delete the  "
                               f"project with id: {project_id}")
        if not delete:
            typer.echo("Not deleting")
            raise typer.Abort()

        session.delete(project)
        session.commit()
        typer.echo("Finished deleting project")

import typer
import json
from sqlalchemy import select
from ramsis.datamodel import Project
from pathlib import Path
from RAMSIS.db import store
from RAMSIS.cli.utils import create_project, update_project

app = typer.Typer()


@app.command()
def create(
        config: Path = typer.Option(
        ...,
        exists=True,
        readable=True,
        help="Path to json project config.")):

    success = store.init_db()
    session = store.session

    if success:
        pass
    else:
        typer.echo(f"Error, db could not be initialized: {success}")
        raise typer.Exit()

    project_names = session.execute(select(Project.name)).scalars().all()

    with open(config, "r") as project_json:
        project_config_list = json.load(project_json)['PROJECTS']

    new_projects = []
    for project_config in project_config_list:
        assert project_config["PROJECT_NAME"] not in project_names, \
            "Project name already exists {project_config['PROJECT_NAME']}"

        project = create_project(project_config)
        store.add(project)
        new_projects.append(project)
    store.save()
    for project in new_projects:
        typer.echo(f"created project {project.name} "
                   f"with id: {project.id}")

    store.close()


@app.command()
def update(
        project_id: int,
        config: Path = typer.Option(
        ...,
        exists=True,
        readable=True,
        help="Path to json project config.")):

    session = store.session

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
    store.save()
    typer.echo(f"updated project {project.name} "
               f"with id: {project.id}")

    store.close()

import json
from pathlib import Path

import typer
from rich.console import Console
from typing_extensions import Annotated

from hermes.actions.crud_models import (delete_project, read_project_oid,
                                        update_project)
from hermes.cli.utils import console_table
from hermes.repositories.database import Session
from hermes.repositories.project import ProjectRepository
from hermes.schemas import Project
from hermes.utils.dateutils import local_to_utc_dict

app = typer.Typer()
console = Console()


@app.command(help="List all Projects.")
def list(
    id: Annotated[bool,
                  typer.Option(
                      "--id", help="Only show IDs and names.")] = False
):
    with Session() as session:
        projects = ProjectRepository.get_all(session)
    if not projects:
        console.print("No projects found")
        return

    if id:  # only show UUIDs and names
        rows = ['oid', 'name']
    else:
        rows = ['name', 'starttime', 'endtime', 'description']

    table = console_table(projects, rows)

    console.print(table)


@app.command(help="Creates a new project.")
def create(
    name: Annotated[str,
                    typer.Argument(
                        help="Name or UUID of the project.")],
    config: Annotated[Path,
                      typer.Option(
                          ..., resolve_path=True, readable=True,
                          help="Path to json Project config file.")]):

    with open(config, "r") as project_file:
        project_config_dict = json.load(project_file)

    project_config_dict = local_to_utc_dict(project_config_dict)

    project = Project(name=name, **project_config_dict)

    with Session() as session:
        project_out = ProjectRepository.create(session, project)
    console.print(f'Successfully created new Project {project_out.name}.')


@app.command(help="Updates an existing project.")
def update(
    name: Annotated[str,
                    typer.Argument(
                        help="Name or UUID of the project.")],
    config: Annotated[Path,
                      typer.Option(
                          ..., resolve_path=True, readable=True,
                          help="Path to json Project config file.")]):
    try:
        with open(config, "r") as project_file:
            project_config_dict = json.load(project_file)

        project_config_dict = local_to_utc_dict(project_config_dict)

        project_oid = read_project_oid(name)
        update_project(project_config_dict, project_oid)
        console.print(f'Successfully updated Project {name}.')
    except Exception as e:
        console.print(str(e))
        raise typer.Exit(code=1)


@app.command(help="Deletes a project.")
def delete(
    name: Annotated[str,
                    typer.Argument(
                        help="Name or UUID of the project.")]):
    try:
        project_oid = read_project_oid(name)
        delete_project(project_oid)
        console.print(f'Successfully deleted Project {name}.')
    except Exception as e:
        console.print(str(e))
        raise typer.Exit(code=1)

import json
from pathlib import Path

import typer
from rich.console import Console
from typing_extensions import Annotated

from hermes.cli.utils import row_table
from hermes.repositories.database import Session
from hermes.repositories.project import ProjectRepository
from hermes.schemas import Project
from hermes.utils.dateutils import local_to_utc_dict

app = typer.Typer()
console = Console()


@app.command(help="List all Projects.")
def list():
    with Session() as session:
        projects = ProjectRepository.get_all(session)
    if not projects:
        console.print("No projects found")
        return

    table = row_table(projects, ['oid', 'name', 'starttime'])

    console.print(table)


@app.command(help="Creates a new project.")
def create(
    name: Annotated[str,
                    typer.Argument(
                        help="Name of the project.")],
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
def update():
    raise NotImplementedError


@app.command(help="Deletes a project.")
def delete():
    raise NotImplementedError

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table
from sqlalchemy.exc import IntegrityError
from typing_extensions import Annotated

from hermes.db import Session
from hermes.repositories.project import ProjectRepository
from hermes.schemas import Project

app = typer.Typer()
console = Console()


@app.command(help="Outputs list of projects")
def list():
    with Session() as session:
        projects = ProjectRepository.get_all(session)
    if not projects:
        console.print("No projects found")
        return
    for project in projects:
        table = Table(show_footer=False,
                      title=f"Project {project.name}",
                      title_justify="left")
        table.add_column("attribute")
        table.add_column("value")
        for attr in ['oid', 'name', 'starttime']:
            table.add_row(attr, str(getattr(
                project, attr)))
    console.print(table)


@app.command(help="Creates a new project")
def create(
    name: Annotated[str,
                    typer.Argument(
                        help="Name of the project")],
    config: Annotated[Path,
                      typer.Option(
                          ..., resolve_path=True, readable=True,
                          help="Path to json project config")]):

    with open(config, "r") as project_file:
        project_config_dict = json.load(project_file)

    project = Project(name=name, **project_config_dict)

    try:
        with Session() as session:
            project_in = ProjectRepository.create(session, project)
            project_out = ProjectRepository.get_one_by_id(
                session, project_in.oid)
            console.print(f'Successfully created new project {project_out}')

    except IntegrityError as e:
        print('Error encountered, probably due to duplicate project name')
        console.print(e.orig)
        raise typer.Exit()

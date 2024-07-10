import json
from pathlib import Path

import typer
from rich.console import Console
from typing_extensions import Annotated

from hermes.cli.utils import row_table
from hermes.db import Session
from hermes.repositories.model import ModelConfigRepository
from hermes.schemas import ModelConfig

app = typer.Typer()
console = Console()


@app.command(help="List all ModelConfigs.")
def list():
    with Session() as session:
        model_config = ModelConfigRepository.get_all(session)
    if not model_config:
        console.print("No ModelConfigs found")
        return

    table = row_table(model_config, ['oid', 'name'])

    console.print(table)


@app.command(help="Create a new ModelConfig.")
def create(
    name: Annotated[str, typer.Argument(help="Name of the ModelConfig.")],
    config: Annotated[Path, typer.Option(
        ..., resolve_path=True, readable=True,
        help="Path to json ModelConfig configuration file.")]
):
    with open(config, "r") as model_config_file:
        model_config_dict = json.load(model_config_file)

    model_config = ModelConfig(name=name, **model_config_dict)

    with Session() as session:
        model_config = ModelConfigRepository.create(session, model_config)

    console.print(f'Successfully created new ModelConfig {model_config.name}.')

from typing import Any

from pydantic import BaseModel
from rich.table import Table
from rich.tree import Tree


def console_table(
        models: list[BaseModel], attributes: list[str]) -> None:
    """
    Displays a table of pydantic objects with the requested attributes.

    :param models: List of pydantic objects to display.
    :param attributes: List of attributes (str) to display as columns.
    """
    # Initialize the Rich console and table
    table = Table()

    # Add the attribute names as column headers
    for attribute in attributes:
        table.add_column(attribute, style="bold")

    # Populate the table rows with the requested attributes of each model
    for model in models:
        row = []
        for attribute in attributes:
            # Use getattr to safely access attributes,
            # default to "N/A" if missing
            value = getattr(model, attribute, "N/A")
            row.append(str(value))
        table.add_row(*row)

    # Print the table to the console
    return table


def console_tree(model: BaseModel, show_none: bool = True) -> None:
    """
    Displays a single pydantic model, including nested dictionaries and lists.

    :param model: A pydantic model to display.
    """

    tree = Tree(f"[bold]{model.__class__.__name__}")

    def add_branch(tree: Tree, key: str, value: Any):
        if isinstance(value, dict):
            branch = tree.add(f"[bold]{key}[/bold]")
            for k, v in value.items():
                add_branch(branch, k, v)
        elif isinstance(value, list):
            branch = tree.add(f"[bold]{key}[/bold]")
            for i, item in enumerate(value):
                add_branch(branch, f"[{i}]", item)
        else:
            tree.add(f"[bold]{key}:[/bold] {value}")

    for field, value in model.model_dump().items():
        if not show_none and value is None:
            continue
        add_branch(tree, field, value)

    return tree

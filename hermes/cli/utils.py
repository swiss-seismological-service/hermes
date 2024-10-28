from rich.table import Table


def row_table(models: list, attributes: list[str]):
    for row in models:
        table = Table(show_footer=False,
                      title="Title",
                      title_justify="left")
        table.add_column("attribute")
        table.add_column("value")
        for attr in attributes:
            table.add_row(attr, str(getattr(
                row, attr)))
    return table

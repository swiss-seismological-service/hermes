import typer

from hermes.cli.project import app as project

app = typer.Typer()
app.add_typer(project, name="project")

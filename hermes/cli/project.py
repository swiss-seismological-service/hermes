import typer

from hermes.db import Session
from hermes.repositories import ProjectRepository
from hermes.schemas import Project

app = typer.Typer()


@app.command()
def create(
        # config: Path = typer.Option(
        # ...,
        # exists=True,
        # readable=True,
        # help="Path to json project config."),
        # catalog_data: typer.FileText = typer.Option(
        # None, help="Path of file containing the "
        # "catalog for forecasts without using fdsnws, e.g. for replays."),
        # well_data: typer.FileText = typer.Option(
        # None, help="Path of file containing inj data for replays ")
):

    project = Project(name="test")
    with Session() as session:
        project_in = ProjectRepository.create(session, project)
        project_out = ProjectRepository.get_one_by_id(session, project_in.oid)
        print(type(project_out))
    # success = init_db(db_url)

    # if success:
    #     pass
    # else:
    #     print(f"Error, db could not be initialized: {success}")
    #     raise typer.Exit()

    # with session_handler(db_url) as session:

    #     with open(config, "r") as project_json:
    #         project_config_dict = json.load(project_json)
    #         project_config_list = project_config_dict['project_configs']

    #     new_projects = []
    #     for project_config in project_config_list:
    #         matching_project = session.execute(
    #             select(Project.name, Project.id).where(
    #                 Project.name == project_config["name"])).first()
    #         if matching_project:
    #             raise Exception(
    #                 "Project name: "
    #                 f"{matching_project.name} already exists "
    #                 f"with id: {matching_project.id}")

    #         project = ProjectConfigurationSchema().load(project_config)
    #         session.add(project)
    #         new_projects.append(project)

    #         if catalog_data:
    #             project.seismiccatalog = catalog_data.read().encode(
    #                 encoding='utf-8')
    #         if well_data:
    #             project.injectionwell = json.dumps(
    #                 [json.loads(well_data.read())],
    #                 ensure_ascii=False).encode(
    #                 encoding='utf-8')
    #         session.commit()

    #     for project in new_projects:
    #         print(f"created project {project.name} "
    #               f"with id: {project.id}")

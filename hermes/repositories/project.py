from hermes.datamodel import ProjectTable
from hermes.repositories import repository_factory
from hermes.schemas import Project


class ProjectRepository(repository_factory(Project, ProjectTable)):
    pass

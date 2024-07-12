from datetime import datetime

from sqlalchemy import text

from hermes.repositories.project import ProjectRepository
from hermes.schemas.project import Project


class TestProject:

    def test_create(self, session, connection):
        project = Project(name='test_project', starttime=datetime.now())
        ProjectRepository.create(session, project)
        project_db = connection.execute(text('SELECT * FROM project'))
        assert len(project_db.all()) == 1

    def test_create2(self, session, connection):
        project = Project(name='test_project', starttime=datetime.now())
        ProjectRepository.create(session, project)
        project_db = connection.execute(text('SELECT * FROM project'))
        assert len(project_db.all()) == 1

# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Tests for the ramsis store module

"""

import os
import unittest

from datetime import datetime

from sqlalchemy import event
from sqlalchemy.sql import select, func

from ramsis.datamodel.seismicity import SeismicityModel, EModel  # noqa
from ramsis.datamodel.project import Project  # noqa
from ramsis.datamodel.seismics import SeismicObservationCatalog, SeismicEvent  # noqa
from RAMSIS.core.builder import default_project  # noqa
from RAMSIS.core.store import Store, EditingContext  # noqa


def make_event(m):
    now = datetime.utcnow()
    return SeismicEvent(magnitude_value=m, x_value=0, y_value=0, z_value=0,
                        datetime_value=now, quakeml=b'')


def load_spatialite(dbapi_conn, connection_record):
    """
    Load spatialite extention.
    """
    # XXX(damb): sudo apt-get install libsqlite3-mod-spatialite
    dbapi_conn.enable_load_extension(True)
    dbapi_conn.load_extension('/usr/lib/x86_64-linux-gnu/mod_spatialite.so')


# XXX(damb): Enable SPATIALITE test cases with:
# $ export RAMSIS_TEST_SPATIALITE="True"; python setup.py test --addopts="-r s"
@unittest.skipUnless(
    os.getenv('RAMSIS_TEST_SPATIALITE', 'False') == 'True',
    "'RAMSIS_TEST_SPATIALITE' envvar not 'True'")
class TestEditingContext(unittest.TestCase):

    def setUp(self):
        self.store = Store('sqlite://')
        event.listen(self.store.engine, 'connect', load_spatialite)

        conn = self.store.engine.connect()
        conn.execute(select([func.InitSpatialMetaData()]))
        conn.close()

        self.store.init_db()

        # We use a simple 1..* relation for these tests
        self.project = default_project(name='TestProject',
                                       starttime=datetime.utcnow())
        self.project.seismiccatalog = SeismicObservationCatalog(
            events=[make_event(m) for m in range(5)])
        self.store.add(self.project)

        self.store.save()
        self.editing_context = EditingContext(self.store)

    def test_separation(self):
        project = self.editing_context.get(self.project)
        project.seismiccatalog.events[0].magnitude_value = 99
        self.assertEqual(self.project.seismiccatalog.events[0].magnitude_value,
                         0, 'Changes in EditingContext should not affect main '
                            'session')

    def test_merge_change(self):
        project = self.editing_context.get(self.project)
        project.seismiccatalog.events[0].magnitude_value = 99
        self.editing_context.save()
        self.assertEqual(self.project.seismiccatalog.events[0].magnitude_value,
                         99, 'Value changes should be merged upon save()')

    def test_merge_deletion(self):
        project = self.editing_context.get(self.project)
        del project.seismiccatalog.events[4]
        self.editing_context.save()
        self.assertEqual(len(self.project.seismiccatalog.events), 4,
                         'Item deletions should be merged upon save()')

    def test_merge_addition(self):
        project = self.editing_context.get(self.project)
        project.seismiccatalog.events.append(make_event(99))
        self.editing_context.save()
        self.assertEqual(len(self.project.seismiccatalog.events), 6,
                         'Item additions should be merged upon save()')

    def test_add_top_level(self):
        project = Project(starttime=datetime.utcnow(), proj_string='4326')
        self.editing_context.add(project)
        self.editing_context.save()
        self.assertEqual(len(self.store.all_projects()), 2,
                         'Top level objects should be merged if they have '
                         'been added.')

    def test_delete_top_level(self):
        project = self.editing_context.get(self.project)
        self.editing_context.delete(project)
        self.editing_context.save()
        self.assertEqual(len(self.store.all_projects()), 0)

    def test_discarded(self):
        project = self.editing_context.get(self.project)
        project.name = 'Foo'
        self.editing_context.save()

        with self.assertRaises(RuntimeError):
            self.editing_context.get(self.project)


class TestStoreInitialization(unittest.TestCase):

    def test_creation(self):
        store = Store('sqlite://')
        self.assertEqual(store.session.get_bind(), store.engine, 'Store must '
                         'have a session bound to its engine after creation')

    # XXX(damb): Enable SPATIALITE test cases with:
    # $ export RAMSIS_TEST_SPATIALITE="True"; \
    #   python setup.py test --addopts="-r s"
    @unittest.skipUnless(
        os.getenv('RAMSIS_TEST_SPATIALITE', 'False') == 'True',
        "'RAMSIS_TEST_SPATIALITE' envvar not 'True'")
    def test_init(self):
        store = Store('sqlite://')
        event.listen(store.engine, 'connect', load_spatialite)

        conn = store.engine.connect()
        conn.execute(select([func.InitSpatialMetaData()]))
        conn.close()

        self.assertFalse(store.is_db_initialized(), 'DB is expected to be '
                         'uninitialized after Store creation')
        store.init_db()
        self.assertTrue(store.is_db_initialized(), 'DB is expected to be '
                        'initialized after call to init_db()')

    def test_close(self):
        store = Store('sqlite://')
        store.close()
        self.assertIsNone(store.session)


# XXX(damb): Enable SPATIALITE test cases with:
# $ export RAMSIS_TEST_SPATIALITE="True"; python setup.py test --addopts="-r s"
@unittest.skipUnless(
    os.getenv('RAMSIS_TEST_SPATIALITE', 'False') == 'True',
    "'RAMSIS_TEST_SPATIALITE' envvar not 'True'")
class TestStoreOperation(unittest.TestCase):

    def setUp(self):
        self.store = Store('sqlite://')
        event.listen(self.store.engine, 'connect', load_spatialite)

        conn = self.store.engine.connect()
        conn.execute(select([func.InitSpatialMetaData()]))
        conn.close()

        self.store.init_db()

    def test_project_creation(self):
        project = default_project(name='TestProject',
                                  starttime=datetime.utcnow())
        self.store.add(project)
        all_projects = self.store.all_projects()
        self.assertEqual(len(all_projects), 1)
        self.assertEqual(all_projects[0], project)

    def test_load_by_name(self):
        project = default_project(name='TestProject',
                                  starttime=datetime.utcnow())
        self.store.add(project)
        test = self.store.load_project('TestProject')
        self.assertEqual(test, project)

    def test_saving(self):
        project = default_project(name='TestProject',
                                  starttime=datetime.utcnow())
        self.store.add(project)

        project.name = 'NewProject'
        self.store.save()
        test = self.store.load_project('NewProject')
        self.assertEqual(test, project)

    def test_model_loading(self):
        seismicity_model = SeismicityModel()
        self.store.session.add(seismicity_model)
        self.store.save()
        test = self.store.load_models()
        self.assertEqual(test[0], seismicity_model)
        test = self.store.load_models(model_type=EModel.SEISMICITY)
        self.assertEqual(test[0], seismicity_model)
        with self.assertRaises(ValueError):
            _ = self.store.load_models(model_type=EModel.HAZARD)

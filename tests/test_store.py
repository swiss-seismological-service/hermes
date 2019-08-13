# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Tests for the ramsis store module

"""

import sys
import types
import unittest
from datetime import datetime
from unittest.mock import MagicMock

from sqlalchemy import String

mock_geoalchemy = types.ModuleType('geoalchemy2')
mock_geoalchemy.Geometry = MagicMock(return_value=String)
sys.modules['geoalchemy2'] = mock_geoalchemy

from RAMSIS.core.store import Store, EditingContext
from ramsis.datamodel.seismicity import SeismicityModel, EModel
from ramsis.datamodel.project import Project
from ramsis.datamodel.seismics import SeismicEvent


def make_event(m):
    now = datetime.now()
    return SeismicEvent(magnitude_value=m, x_value=0, y_value=0, z_value=0,
                          datetime_value=now, quakeml=b'')


class TestEditingContext(unittest.TestCase):

    def setUp(self):
        self.store = Store('sqlite://')
        # Mock any geometry columns

        self.store.init_db()
        # We use a simple 1:* relation for these tests
        self.project = self.store.create_project({'starttime': datetime.now(),
                                                  'spatialreference': '4326'})
        self.project.seismiccatalog.events = [make_event(m) for m in range(5)]
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
        project = Project(starttime=datetime.now(), spatialreference='4326')
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


class TestStoreInitialization(unittest.TestCase):

    def test_creation(self):
        store = Store('sqlite://')
        self.assertEqual(store.session.get_bind(), store.engine, 'Store must '
                         'have a session bound to its engine after creation')

    def test_init(self):
        store = Store('sqlite://')
        self.assertFalse(store.is_db_initialized(), 'DB is expected to be '
                         'uninitialized after Store creation')
        store.init_db()
        self.assertTrue(store.is_db_initialized(), 'DB is expected to be '
                        'initialized after call to init_db()')

    def test_close(self):
        store = Store('sqlite://')
        store.close()
        self.assertIsNone(store.session)


class TestStoreOperation(unittest.TestCase):

    def setUp(self):
        self.store = Store('sqlite://')
        self.store.init_db()

    def test_project_creation(self):
        project = self.store.create_project({'starttime': datetime.now(),
                                             'spatialreference': '4326'})
        all_projects = self.store.all_projects()
        self.assertEqual(len(all_projects), 1)
        self.assertEqual(all_projects[0], project)

    def test_load_by_name(self):
        project = self.store.create_project({'name': 'test_project',
                                             'starttime': datetime.now(),
                                             'spatialreference': '4326'})
        test = self.store.load_project('test_project')
        self.assertEqual(test, project)

    def test_saving(self):
        project = self.store.create_project({'name': 'test_project',
                                             'starttime': datetime.now(),
                                             'spatialreference': '4326'})
        project.name = 'new name'
        self.store.save()
        test = self.store.load_project('new name')
        self.assertEqual(test, project)

    def test_model_loading(self):
        seismicity_model = SeismicityModel()
        self.store.session.add(seismicity_model)
        self.store.save()
        test = self.store.load_models()
        self.assertEqual(test[0], seismicity_model)
        test = self.store.load_models(model_type=EModel.SEISMICITY)
        self.assertEqual(test[0], seismicity_model)
        test = self.store.load_models(model_type=EModel.HAZARD)
        self.assertEqual(len(test), 0)

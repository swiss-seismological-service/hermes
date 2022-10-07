# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
RT-RAMSIS low level data access layer

The `store` abstracts away low level data access by providing methods
to query and create top level data-model entities. It handles the db session
and connection engine over the life cycle of the app.

"""
import logging
import pkgutil
import re
import sys

from functools import wraps
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker, with_polymorphic, scoped_session

import ramsis.datamodel
from ramsis.datamodel.base import ORMBase
from ramsis.datamodel import Project, EModel, Model, SeismicityModel, HazardModel

logger = logging.getLogger(__name__)

# We need to make sure all datamodel modules are imported at least once
# for the ORMBase meta data to be complete; ensure that ORMBase has all the
# metadata
pkg = ramsis.datamodel
modules = pkgutil.walk_packages(pkg.__path__, prefix=pkg.__name__ + '.')
modules = [m for m in modules if 'tests' not in m[1]]
for finder, module_name, _ in modules:
    if module_name not in sys.modules:
        finder.find_module(module_name).load_module(module_name)


def with_session_validation(method):
    """
    Method decorator performing a session validation.
    """

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        if not self._editing_session:
            raise RuntimeError(f'Invalid session: {self._editing_session}.')

        return method(self, *args, **kwargs)

    return wrapper


class Store:

    def __init__(self, db_url):
        """
        :param str db_url: Fully qualified database url (including user & pw)

        """
        starred_url = re.sub("(?<=:)([^@:]+)(?=@[^@]+$)", "***", db_url)
        logger.info(f'Opening DB connection at {starred_url}')
        self.engine = create_engine(db_url, echo=False)
        # TODO LH: reconsider the use of expire_on_commit=False
        self.make_session = scoped_session(sessionmaker(
            bind=self.engine, expire_on_commit=False,
            autocommit=False, autoflush=False))
        self.session = self.make_session

    def init_db(self):
        """
        Initializes the db

        Creates the table defined in the ORM meta data.

        :returns: True if successful
        :rtype: bool
        """
        try:
            ORMBase.metadata.create_all(self.engine, checkfirst=True)
        except SQLAlchemyError as e:
            logger.error(f'Error while initializing DB: {e}')
            return False
        return True

    def get_fresh(self, obj):
        """
        Refresh the objects

        :param obj: Data model object to be added
        """
        if obj:
            new_obj = self.session.query(type(obj)).\
                populate_existing().get(obj.id)
            return new_obj

    def merge(self, obj):
        """
        Register a newly created object by merging it with already existing
        instances of the object. This avoids duplicate primary key errors.

        :param obj: Data model object to be added
        """
        self.session.merge(obj)

    def add(self, obj):
        """
        Register a newly created object

        :param obj: Data model object to be added
        """
        self.session.add(obj)

    def delete(self, obj):
        """
        Delete any object from the store

        :param obj: Data model object to be deleted
        """
        self.session.delete(obj)

    def flush(self):
        """
        Flush the session changes
        """
        self.session.flush()

    def save(self):
        """
        Save the session changes with commit
        """
        self.session.commit()

    def close(self):
        """
        Close session by removing it
        """
        self.session.remove()

    def all_projects(self):
        """
        Return a list of all projects

        :return: List of projects
        :rtype: [ramsis.datamodel.project.Project]
        """
        return self.session.query(Project).all()

    def load_project(self, project_name):
        """
        Load RAMSIS project by name

        :param str project_name: Name of the project to open


        :return: Newly created project
        :rtype: ramsis.datamodel.project.Project

        """
        logger.info(f'Opening project {project_name} ')
        project = self.session.query(Project).\
            filter(Project.name == project_name).\
            first()
        return project

    def load_models(self, model_type=None):
        """
        Load all models by model type.

        If `model_type` is not provided, all available models will be returned.

        :param ramsis.datamodel.model.EModel model_type: Model type specifier
        :return: List of models
        :rtype: [ramsis.datamodel.model.Model]
        """
        _map = {
            EModel.SEISMICITY: SeismicityModel,
            EModel.HAZARD: HazardModel, }

        try:
            entity = _map[model_type]
        except KeyError:
            if model_type is not None:
                raise ValueError(f'Unknown model type {model_type!r}')

            entity = with_polymorphic(Model, '*')

        return self.session.query(entity).all()

    def load_models_by(self, entity, **kwargs):
        return self.session.query(entity).filter_by(**kwargs).all()

    def test_connection(self):
        try:
            self.engine.connect()
        except OperationalError as e:
            logger.warning(f'Connection test failed with {e}')
            return False
        else:
            return True

    def is_db_initialized(self):
        """
        Check if the DBis empty and ready for initialization

        :return: True if we're connected to an empty DB
        """
        expected_tables = ORMBase.metadata.tables.keys()
        if all(tn in self.engine.table_names() for tn in expected_tables):
            return True
        return False

# TODO look at removal, I think this was useful for
# the GUI, but believe everything can be done with scoped
# session.


class EditingContext:
    """
    A temporary context for editing data model objects

    The editing context provides temporary copies of data model objects for
    editing. When the editing context is saved, the changes will be committed
    to the database. When the editing context is discarded, all changes to
    objects inside the context will be discarded with it.

    .. note: An `EditingContext` should be discarded after saving.

    """

    def __init__(self, store):
        """

        :param store: The main store from which objects to edit are pulled in
        """
        self._store = store
        self._editing_session = store.make_session()
        self._edited = set()

    @with_session_validation
    def get(self, obj):
        """
        Get a copy of `object` that is ready for editing.

        .. note: Any edits to related objects will be saved too when invoking
                 :meth:`save()'.

        :param obj: Data model object to copy for editing

        """
        editing_copy = self._editing_session.merge(obj, load=True)
        self._edited.add(editing_copy)
        return editing_copy

    @with_session_validation
    def add(self, obj):
        """
        Register a newly created top level object

        If a new toplevel object is created during editing that has no
        relation to any object obtained through :meth:`get()`, it needs to be
        :meth:`add()`ed to the editing context before saving.

        :param obj: Data model object to add to the context

        """
        self._edited.add(obj)

    @with_session_validation
    def delete(self, obj):
        """
        Mark a top-level object for deletion

        Usage example:

            editable_project = editing_context.get(project)
            editing_context.delete(editable_project)
            editing_context.save()

        .. note: Objects that are reachable through relationships of previously
                 obtained objects (either through :meth:`add` or :meth:`get`)
                 usually don't have to be marked for deletion explicitly.
                 They are typically marked when they become orphans, e.g.:

                     catalog.events.remove(event_x)

        :param obj: Data model object to mark for deletion

        """
        self._editing_session.delete(obj)

    @with_session_validation
    def save(self):
        """
        Save edits to the main store and the database

        .. note: The editing context should be discarded after saving since all
                 objects will have been expunged and the underlying session
                 closed.

        """
        for obj in self._edited:
            original = self._store.session.merge(obj)
            # We need to propagate deletes manually since the instance state is
            # not updated until flush() (and flushing the editing session
            # causes other issues
            if obj in self._editing_session.deleted:
                self._store.delete(original)
        self._editing_session.commit()
        self._editing_session.close()
        self._store.save()

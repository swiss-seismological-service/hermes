# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
RT-RAMSIS low level data access layer

The `store` abstracts away low level data access by providing methods
to query and create top level data-model entities. It handles the db session
and connection engine over the life cycle of the app.

"""

import re
import logging
import pkgutil
import sys
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import sessionmaker, RelationshipProperty
from sqlalchemy.ext.declarative.clsregistry import _ModuleMarker
import ramsis.datamodel
from ramsis.datamodel.project import Project
from ramsis.datamodel.seismics import SeismicCatalog
from ramsis.datamodel.settings import ProjectSettings
from ramsis.datamodel.model import Model, ORMBase


logger = logging.getLogger(__name__)

# We need to make sure all datamodel modules are imported at least once
# for the ORMBase meta data to be complete
# Make sure ORMBase has all the metadata
pkg = ramsis.datamodel
modules = pkgutil.walk_packages(pkg.__path__, prefix=pkg.__name__+'.')
for finder, module_name, _ in modules:
    if module_name not in sys.modules:
        finder.find_module(module_name).load_module(module_name)


class Store:

    def __init__(self, db_url):
        """
        :param str db_url: Fully qualified database url (including user & pw)

        """
        starred_url = re.sub("(?<=:)([^@:]+)(?=@[^@]+$)", "***", db_url)
        logger.info(f'Opening DB connection at {starred_url}')
        self.engine = create_engine(db_url)
        session = sessionmaker(bind=self.engine, expire_on_commit=False)
        self.session = session()

    def init_db(self):
        """
        Initializes the db

        Creates the table defined in the ORM meta data.

        :returns: True if successful
        :rtype: bool
        """
        logger.info('Initializing DB')
        try:
            ORMBase.metadata.create_all(self.engine, checkfirst=True)
        except SQLAlchemyError as e:
            logger.error(f'Error while initializing DB: {e}')
            return False
        return True

    def save(self):
        self.session.commit()

    def close(self):
        logger.info(f'Closing DB connection')
        self.session.close()
        self.session = None

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

    def create_project(self, init_args):
        """
        Create a new project and return it.

        Creates and bootstraps a new project structure. If a project with the
        same name exists it will be replaced.

        :param dict init_args: Dictionary containing initialization arguments
            for the project
        :return: Newly created project
        :rtype: ramsis.datamodel.project.Project

        """
        logger.info(f'Creating project {init_args.get("name", "unnamed")}')
        project = Project(**init_args)
        self.session.add(project)
        self.session.commit()
        return project

    def load_models(self, model_type=None):
        """
        Load all models by model type.

        If `model_type` is not provided, all available models will be returned.

        :param ramsis.datamodel.model.EModel model_type: Model type specifier
        :return: List of models
        :rtype: [ramsis.datamodel.model.Model]
        """
        models = self.session.query(Model)
        if model_type:
            models.filter(Model._type == model_type)
        return models.all()

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

    def is_sane(self):
        """
        Check whether the current database matches our model

        Currently we check that all tables exist with all columns. What is not
        checked

        * Column types are not verified
        * Relationships are not verified at all (TODO)

        :return: True if all declared models have corresponding tables and
            columns.
        """

        engine = self.session.get_bind()
        iengine = inspect(engine)

        errors = False

        tables = iengine.get_table_names()

        # Go through all SQLAlchemy models
        for name, klass in ORMBase._decl_class_registry.items():

            if isinstance(klass, _ModuleMarker):
                # Not a model
                continue

            table = klass.__tablename__
            if table in tables:
                # Check all columns are found
                # Looks like
                # [{'default': "nextval('sanity_check_test_id_seq'::regclass)",
                #   'autoincrement': True, 'nullable': False, 'type': INTEGER(),
                #   'name': 'id'}]

                columns = [c["name"] for c in iengine.get_columns(table)]
                mapper = inspect(klass)

                for column_prop in mapper.attrs:
                    if isinstance(column_prop, RelationshipProperty):
                        # TODO: Add sanity checks for relations
                        pass
                    else:
                        for column in column_prop.columns:
                            # Assume normal flat column
                            if not column.key in columns:
                                logger.error(f'Model {klass} declares column '
                                             f'{column.key} which does not exist '
                                             f'in database {engine}')
                                errors = True
            else:
                logger.error(f'Model {klass} declares table {table} which does not '
                             f'exist in database {engine}')
                errors = True

        return not errors

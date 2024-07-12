
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import MetaData
from sqlalchemy.sql import text

from config import get_settings
from hermes.datamodel import ORMBase

settings = get_settings()
EXTENSIONS = ['postgis', 'postgis_topology']


def create_extensions(engine):
    with engine.connect() as conn:
        for extension in EXTENSIONS:
            conn.execute(
                text(f'CREATE EXTENSION IF NOT EXISTS "{extension}"'))
            conn.commit()


def create_engine(url: URL, **kwargs) -> Engine:
    _engine = _create_engine(
        url,
        future=True,
        pool_size=settings.POSTGRES_POOL_SIZE,
        max_overflow=settings.POSTGRES_MAX_OVERFLOW,
        **kwargs,
    )
    create_extensions(_engine)
    return _engine


engine = create_engine(settings.SQLALCHEMY_DATABASE_URL)
Session = sessionmaker(engine, expire_on_commit=True)


def _create_tables():
    ORMBase.metadata.create_all(engine)


def _drop_tables():

    m = MetaData()
    m.reflect(engine, schema='public')
    tables = [
        table for table in m.sorted_tables if table.name not in
        ['spatial_ref_sys']]
    m.drop_all(engine, tables=tables)

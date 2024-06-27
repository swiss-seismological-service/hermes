
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.engine import URL, Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import MetaData

from config import get_settings
from hermes.datamodel import ORMBase, ProjectTable  # noqa

settings = get_settings()


def create_engine(url: URL, **kwargs) -> Engine:
    return _create_engine(
        url,
        future=True,
        pool_size=settings.POSTGRES_POOL_SIZE,
        max_overflow=settings.POSTGRES_MAX_OVERFLOW,
        **kwargs,
    )


engine = create_engine(settings.SQLALCHEMY_DATABASE_URL)
Session = sessionmaker(engine, expire_on_commit=True)


async def _create_db():
    ORMBase.metadata.create_all(engine)


async def _drop_db():
    """Drops all database Tables but leaves the DB itself in place"""
    m = MetaData()
    m.reflect(engine)
    m.drop_all(engine)


import pandas as pd
from sqlalchemy import Select
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.engine import URL, Engine
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.session import Session
from sqlalchemy.schema import MetaData
from sqlalchemy.sql import text

from hermes.config import get_settings
from hermes.datamodel.base import ORMBase

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
DatabaseSession = sessionmaker(engine, expire_on_commit=True)


def _create_tables():
    ORMBase.metadata.create_all(engine)


def _drop_tables():
    m = MetaData()
    m.reflect(engine, schema='public')
    tables = [
        table for table in m.sorted_tables if table.name not in
        ['spatial_ref_sys']]
    m.drop_all(engine, tables=tables)


def _check_tables_exist():
    """
    Check if tables exist in the database,
    assuming that if there are more than 5
    tables, the database is initialized.
    """
    m = MetaData()
    m.reflect(engine, schema='public')
    tables = [table for table in m.sorted_tables]
    return len(tables) > 5


def pandas_read_sql(stmt: Select, session: Session):
    df = pd.read_sql_query(stmt, session.connection())
    return df


async def pandas_read_sql_async(stmt, session: AsyncSession):
    """
    Execute a SQLAlchemy Select statement asynchronously,
    and load results into a DataFrame using pd.read_sql.
    """
    def read_sql_sync(connection, statement):
        return pd.read_sql(statement, connection)

    # Compile SQLAlchemy statement to raw SQL string
    compiled_stmt = stmt.compile(
        compile_kwargs={"literal_binds": True},
        dialect=session.bind.dialect
    )

    connection = await session.connection()
    # Important: Extract a DBAPI-compatible connection explicitly

    df = await connection.run_sync(read_sql_sync, str(compiled_stmt))
    return df

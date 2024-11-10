from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    POSTGRES_HOST: str = 'postgres'
    POSTGRES_PORT: str = '5432'
    POSTGRES_USER: str = 'postgres'
    POSTGRES_PASSWORD: str
    POSTGRES_DB: str = 'postgres'

    POSTGRES_POOL_SIZE: int = 5
    POSTGRES_MAX_OVERFLOW: int = 10

    # Timezone of the DATA, eg. if 'UTC', all datetime which are passed
    # via CLI and configuration files will be converted from the operators
    # system timezone to UTC before querying data and running forecasts.
    # TODO: Implement for configuration files.
    TIMEZONE: str | None = None

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> URL:
        return URL.create(
            drivername='postgresql+psycopg2',
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB
        )

    @property
    def ASYNC_SQLALCHEMY_DATABASE_URL(self) -> URL:
        return URL.create(
            drivername='postgresql+asyncpg',
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB
        )


@lru_cache()
def get_settings():
    return Settings()

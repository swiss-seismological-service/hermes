
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class Model(BaseModel):
    model_config = ConfigDict(extra='allow',
                              arbitrary_types_allowed=True,
                              from_attributes=True)


class CreationInfoMixin(Model):
    creationinfo_author: str | None = None
    creationinfo_agencyid: str | None = None
    creationinfo_creationtime: datetime = None
    creationinfo_version: str | None = None

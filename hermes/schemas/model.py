from datetime import datetime
from uuid import UUID

from hermes.schemas.base import EResultType, Model


class ModelConfig(Model):
    oid: UUID | None = None
    name: str | None = None
    enabled: bool = True
    description: str | None = None
    result_type: EResultType | None = None
    sfm_module: str | None = None
    sfm_function: str | None = None
    last_modified: datetime | None = None

    config: dict = {}

    tags: list[str] = []

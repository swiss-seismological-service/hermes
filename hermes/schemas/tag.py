from uuid import UUID

from hermes.schemas.base import Model


class Tag(Model):
    oid: UUID | None = None
    name: str | None = None

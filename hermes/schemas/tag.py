from uuid import UUID, uuid4

from hermes.schemas.base import Model


class Tag(Model):
    oid: UUID = uuid4()
    name: str

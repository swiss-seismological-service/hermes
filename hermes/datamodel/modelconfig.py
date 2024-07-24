from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, Column, String
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from hermes.datamodel.base import NameMixin, ORMBase
from hermes.datamodel.tag import tag_model_config_association


class ModelConfigTable(ORMBase, NameMixin):

    description = Column(String)
    enabled = Column(Boolean, default=True)
    result_type = Column(String(15), nullable=False)

    # The model should be called by sfm_module.sfm_function(*args)
    sfm_module = Column(String)
    sfm_function = Column(String)

    last_modified = Column(TIMESTAMP(precision=0),
                           default=datetime.now(timezone.utc),
                           onupdate=datetime.now(timezone.utc))

    config = Column(JSON, nullable=False)

    modelruns = relationship('ModelRunTable',
                             back_populates='modelconfig')

    _tags = relationship('TagTable',
                         back_populates='modelconfigs',
                         secondary=tag_model_config_association)

    @hybrid_property
    def tags(self):
        t = [tag.name for tag in self._tags]
        return t

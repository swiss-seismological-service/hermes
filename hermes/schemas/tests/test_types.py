from datetime import datetime

import pytest
from pydantic import BaseModel

from hermes.schemas.types import DatetimeString


def test_datetime_string():
    class Model(BaseModel):
        date: DatetimeString

    model = Model(date='2024-07-01T00:00:00')
    assert model.date == '2024-07-01T00:00:00'

    model = Model(date=datetime(2024, 7, 1))
    assert model.date == '2024-07-01T00:00:00'

    with pytest.raises(ValueError):
        Model(date='string')

    with pytest.raises(ValueError):
        Model(date=1)

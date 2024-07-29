from datetime import datetime

import pytest
from pydantic import BaseModel

from hermes.schemas.base import DatetimeString, real_value_mixin


def test_real_value_mixin():
    class Test(real_value_mixin('test', str)):
        pass

    Test(test_value='1', test_uncertainty=2, test_loweruncertainty=3,
         test_upperuncertainty=4, test_confidencelevel=5)


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

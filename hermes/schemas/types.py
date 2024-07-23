from datetime import datetime

from pydantic import BeforeValidator
from typing_extensions import Annotated


def sd_validator(val):
    if isinstance(val, datetime):
        return val.strftime('%Y-%m-%dT%H:%M:%S')
    elif isinstance(val, str):
        try:
            datetime.strptime(val, '%Y-%m-%dT%H:%M:%S')
            return val
        except Exception:
            raise ValueError('Invalid datetime string.')
    else:
        raise ValueError('Invalid datetime format. Please '
                         'provide a datetime object or a string '
                         'in the format %Y-%m-%dT%H:%M:%S.')


DatetimeString = Annotated[
    str,
    BeforeValidator(sd_validator),
    'Datetime string in the format %Y-%m-%dT%H:%M:%S or a datetime object.'
]

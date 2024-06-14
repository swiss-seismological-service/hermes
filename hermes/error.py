
# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Error Utilities
"""

import enum

import requests


class RamsisError(Exception):
    """General error for RAMSIS"""


class RemoteWorkerError(RamsisError):
    """Error recieved back from Remote Worker that calls seismicity model"""


class ExitCode(enum.Enum):
    EXIT_SUCCESS = 0
    EXIT_WARNING = 1
    EXIT_ERROR = 2


class Error(Exception):
    """Error base class"""
    exit_code = ExitCode.EXIT_ERROR.value
    traceback = False

    def __init__(self, *args):
        super().__init__(*args)
        self.args = args

    def get_message(self):
        return type(self).__doc__.format(*self.args)

    __str__ = get_message


class ErrorWithTraceback(Error):
    """Error with traceback."""
    traceback = True


class _IOError(Error):
    """Base IO error ({})."""


class RequestsError(requests.exceptions.RequestException, _IOError):
    """Base request error ({})."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class NoContent(RequestsError):
    """The request '{}' is returning no content ({})."""


class ClientError(RequestsError):
    """Response code not OK ({})."""

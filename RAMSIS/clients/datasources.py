# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Data fetching facilities.
"""
import json
import contextlib
import requests
import io
import logging
from requests import get, exceptions
from prefect import get_run_logger
from prefect.exceptions import MissingContextError

from RAMSIS.config import FDSNWS_NOCONTENT_CODES
from RAMSIS.error import RequestsError, NoContent, ClientError


@contextlib.contextmanager
def binary_request(request, url, params={}, timeout=None,
                   nocontent_codes=(203,), **kwargs):
    """
    Make a binary request

    :param request: Request object to be used
    :type request: :py:class:`requests.Request`
    :param str url: URL
    :params dict params: Dictionary of query parameters
    :param timeout: Request timeout
    :type timeout: None or int or tuple

    :rtype: io.BytesIO
    """
    try:
        r = request(url, params=params, timeout=timeout, **kwargs)
        if r.status_code in nocontent_codes:
            raise NoContent(r.url, r.status_code, response=r)

        r.raise_for_status()
        print("response status code", r.status_code, r.status_code != 200)
        if r.status_code != 200:
            raise ClientError(r.status_code, response=r)

        yield io.BytesIO(r.content)

    except (NoContent, ClientError) as err:
        raise err
    except requests.exceptions.RequestException as err:
        raise RequestsError(err, response=err.response)


class HYDWSDataSource:
    """
    Fetching and deserializing data from *HYDWS*.
    """

    def __init__(self, url, timeout=None):
        self.url = url
        self._timeout = timeout

        self._args = {}
        try:
            self.logger = get_run_logger()
        except MissingContextError:
            self.logger = logging.getLogger("HYDWSDataSource")

    def fetch(self, **kwargs):
        """
        :param kwargs: args dict forwarded to the HYDWS
        """
        self._args = kwargs
        bh = self.run()
        return bh

    def run(self):
        bh = None

        self.logger.info(
            f"Request borehole / hydraulic data from hydws (url={self.url}, "
            f"params={self._args}).")
        try:
            with binary_request(
                get, self.url, self._args, self._timeout,
                    nocontent_codes=FDSNWS_NOCONTENT_CODES) as ifd:
                bh = json.load(ifd)

        except NoContent:
            self.logger.info(f'No data received from {self.url}')
            raise
        except RequestsError as err:
            self.logger.error(
                f"Error while fetching data from {self.url} ({err}).")
            raise
        except exceptions.Timeout as err:
            self.logger.error(f"The request timed out to {self.url}, ({err})")
            raise
        else:
            if bh["sections"]:
                msg = ('Received borehole data '
                       f'(sections={len(bh["sections"])})')
                if bh["sections"][0]["hydraulics"]:
                    msg += f', samples={len(bh["sections"][0]["hydraulics"])}'
                msg += ').'

                self.logger.info(msg)

        return bh


class FDSNWSDataSource:
    """
    Fetches seismic event data from a web service.
    """

    def __init__(self, url, timeout=None):
        self.url = url
        self._timeout = timeout

        self._args = {}
        try:
            self.logger = get_run_logger()
        except MissingContextError:
            self.logger = logging.getLogger("FDSNWSDataSource")

    def fetch(self, **kwargs):
        self._args = kwargs
        cat = self.run()
        return cat

    def run(self):
        cat = None

        self.logger.info(
            f"Request seismic catalog from fdsnws-event (url={self.url}, "
            f"params={self._args}).")
        try:
            with binary_request(
                get, self.url, self._args, self._timeout,
                    nocontent_codes=FDSNWS_NOCONTENT_CODES) as ifd:
                cat = ifd.read()
        except NoContent:
            self.logger.info(f'No data received from {self.url}')
            raise
        except RequestsError as err:
            self.logger.error(
                f"Error while fetching data from {self.url} ({err}).")
            raise
        except exceptions.Timeout as err:
            self.logger.error(
                f"The request timed out to {self.url}, ({err})")
            raise

        return cat

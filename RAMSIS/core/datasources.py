# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Data fetching facilities.
"""
import json
import requests
from prefect import get_run_logger

from RAMSIS.config import FDSNWS_NOCONTENT_CODES
from ramsis.utils.clients import (binary_request,
                                  NoContent, RequestsError)


class HYDWSDataSource():
    """
    Fetching and deserializing data from *HYDWS*.
    """

    def __init__(self, url, timeout=None):
        self.url = url
        self._timeout = timeout

        self._args = {}
        self.enabled = False
        self.logger = get_run_logger()

    def fetch(self, **kwargs):
        """
        :param kwargs: args dict forwarded to the HYDWS
        """
        self._args = kwargs
        if self.enabled:
            bh = self.run()
        return bh

    def run(self):
        bh = None

        self.logger.info(
            f"Request borehole / hydraulic data from hydws (url={self.url}, "
            f"params={self._args}).")
        try:
            with binary_request(
                requests.get, self.url, self._args, self._timeout,
                    nocontent_codes=FDSNWS_NOCONTENT_CODES) as ifd:
                bh = json.load(ifd)

        except NoContent:
            self.logger.info(f'No data received from {self.url}')
            raise
        except RequestsError as err:
            self.logger.error(
                f"Error while fetching data from {self.url} ({err}).")
            raise
        except requests.exceptions.Timeout as err:
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


class FDSNWSDataSource():
    """
    Fetches seismic event data from a web service.
    """

    def __init__(self, url, timeout=None):
        self.url = url
        self._timeout = timeout

        self._args = {}
        self.enabled = False
        self.logger = get_run_logger()

    def fetch(self, **kwargs):
        self._args = kwargs
        if self.enabled:
            cat = self.run()
        return cat

    def run(self):
        cat = None

        self.logger.info(
            f"Request seismic catalog from fdsnws-event (url={self.url}, "
            f"params={self._args}).")
        try:
            with binary_request(
                requests.get, self.url, self._args, self._timeout,
                    nocontent_codes=FDSNWS_NOCONTENT_CODES) as ifd:
                cat = ifd.read()
        except NoContent:
            self.logger.info(f'No data received from {self.url}')
            raise
        except RequestsError as err:
            self.logger.error(
                f"Error while fetching data from {self.url} ({err}).")
            raise
        except requests.exceptions.Timeout as err:
            self.logger.error(
                f"The request timed out to {self.url}, ({err})")
            raise

        return cat

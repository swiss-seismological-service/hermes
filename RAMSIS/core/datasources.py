# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Data fetching facilities.
"""

import logging

import requests

from PyQt5 import QtCore

from RAMSIS.config import FDSNWS_NOCONTENT_CODES
from RAMSIS.io.hydraulics import (HYDWSBoreholeHydraulicsDeserializer,
                                  HYDWSJSONIOError)
from RAMSIS.io.seismics import (QuakeMLCatalogDeserializer,
                                QuakeMLCatalogIOError)
from RAMSIS.io.utils import (binary_request, pymap3d_transform_geodetic2ned,
                             NoContent, RequestsError)


class HYDWSDataSource(QtCore.QThread):
    """
    QThread fetching and deserializing data from *HYDWS*.
    """
    DESERIALZER = HYDWSBoreholeHydraulicsDeserializer

    data_received = QtCore.pyqtSignal(object)

    def __init__(self, url, timeout=None, proj=None):
        super().__init__()
        self.url = url

        self._args = {}
        self.enabled = False
        self.logger = logging.getLogger(__name__)

        self._deserializer = self.DESERIALZER(
            proj=proj,
            transform_callback=pymap3d_transform_geodetic2ned)

    def fetch(self, **kwargs):
        """
        Fetch data by means of a background-thread

        :param kwargs: args dict forwarded to the HYDWS
        """
        self._args = kwargs
        if self.enabled:
            self.start()

    def run(self):
        bh = None

        self.logger.debug(
            f"Request seismic catalog from fdsnws-event (url={self._url}, "
            f"params={self._params}).")
        try:
            with binary_request(
                requests.get, self.url, self._args, self._timeout,
                    nocontent_codes=FDSNWS_NOCONTENT_CODES) as ifd:
                bh = self._deserializer.load(ifd)

        except NoContent:
            self.logger.info('No data received.')
        except RequestsError as err:
            self.logger.error(f"Error while fetching data ({err}).")
        except HYDWSJSONIOError as err:
            self.logger.error(f"Error while deserializing data ({err}).")
        else:
            self.logger.info(
                f"Received borehole data with {len(bh)} sections.")

        self.data_received.emit(bh)


class FDSNWSDataSource(QtCore.QThread):
    """
    Fetches seismic event data from a web service in the background.
    """

    DESERIALZER = QuakeMLCatalogDeserializer

    data_received = QtCore.pyqtSignal(object)

    def __init__(self, url, timeout=None, proj=None):
        super().__init__()
        self.url = url
        self._timeout = None

        self._args = {}
        self.enabled = False
        self.logger = logging.getLogger(__name__)

        self._deserializer = self.DESERIALZER(
            proj=proj,
            transform_callback=pymap3d_transform_geodetic2ned)

    def fetch(self, **kwargs):
        """
        Fetch data by means of a background-thread

        :param kwargs: args dict forwarded to fdsnws-event
        """
        self._args = kwargs
        if self.enabled:
            self.start()

    def run(self):
        cat = None

        self.logger.debug(
            f"Request seismic catalog from fdsnws-event (url={self._url}, "
            f"params={self._params}).")
        try:
            with binary_request(
                requests.get, self.url, self._args, self._timeout,
                    nocontent_codes=FDSNWS_NOCONTENT_CODES) as ifd:
                cat = self._deserializer.load(ifd)

        except NoContent:
            self.logger.info('No data received.')
        except RequestsError as err:
            self.logger.error(f"Error while fetching data ({err}).")
        except QuakeMLCatalogIOError as err:
            self.logger.error(f"Error while deserializing data ({err}).")
        else:
            self.logger.info(
                f"Received catalog with {len(cat)} events.")

        self.data_received.emit(cat)

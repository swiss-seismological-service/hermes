# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Data fetching facilities.
"""

import logging

import requests

from PyQt5 import QtCore

from RAMSIS.config import FDSNWS_NOCONTENT_CODES
from ramsis.io.hydraulics import (HYDWSBoreholeHydraulicsDeserializer,
                                  HYDWSJSONIOError)
from ramsis.io.seismics import (QuakeMLObservationCatalogDeserializer,
                                QuakeMLCatalogIOError)
from ramsis.utils.clients import (binary_request,
                                  NoContent, RequestsError)


class HYDWSDataSource(QtCore.QThread):
    """
    QThread fetching and deserializing data from *HYDWS*.
    """
    DESERIALZER = HYDWSBoreholeHydraulicsDeserializer

    data_received = QtCore.pyqtSignal(object)

    def __init__(self, url, project, timeout=None):
        super().__init__()
        self.url = url
        self._timeout = timeout

        self._args = {}
        self.enabled = False
        self.logger = logging.getLogger(__name__)

        self._deserializer = self.DESERIALZER(
            ramsis_proj=project.spatialreference,
            external_proj=4326,
            ref_easting=project.referencepoint_x,
            ref_northing=project.referencepoint_y,
            transform_func_name='pyproj_transform_to_local_coords')

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

        self.logger.info(
            f"Request borehole / hydraulic data from hydws (url={self.url}, "
            f"params={self._args}).")
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
            if bh.sections:
                msg = f'Received borehole data (sections={len(bh.sections)}'
                if bh.sections[0].hydraulics:
                    msg += f', samples={len(bh.sections[0].hydraulics)}'
                msg += ').'

                self.logger.info(msg)

        self.data_received.emit(bh)


class FDSNWSDataSource(QtCore.QThread):
    """
    Fetches seismic event data from a web service in the background.
    """

    DESERIALZER = QuakeMLObservationCatalogDeserializer

    data_received = QtCore.pyqtSignal(object)

    def __init__(self, url, project, timeout=None):
        super().__init__()
        self.url = url
        self._timeout = timeout

        self._args = {}
        self.enabled = False
        self.logger = logging.getLogger(__name__)

        self._deserializer = self.DESERIALZER(
            ramsis_proj=project.spatialreference,
            external_proj=4326,
            ref_easting=project.referencepoint_x,
            ref_northing=project.referencepoint_y,
            transform_func_name='pyproj_transform_to_local_coords')

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

        self.logger.info(
            f"Request seismic catalog from fdsnws-event (url={self.url}, "
            f"params={self._args}).")
        try:
            with binary_request(
                requests.get, self.url, self._args, self._timeout,
                    nocontent_codes=FDSNWS_NOCONTENT_CODES) as ifd:
                print(ifd, type(ifd))
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

# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Data fetching facilities.
"""

import prefect
import requests

from RAMSIS.config import FDSNWS_NOCONTENT_CODES
from ramsis.io.hydraulics import (HYDWSBoreholeHydraulicsDeserializer,
                                  HYDWSJSONIOError)
from ramsis.io.seismics import (QuakeMLObservationCatalogDeserializer,
                                QuakeMLCatalogIOError)
from ramsis.utils.clients import (binary_request,
                                  NoContent, RequestsError)


class HYDWSDataSource():
    """
    Fetching and deserializing data from *HYDWS*.
    """
    DESERIALZER = HYDWSBoreholeHydraulicsDeserializer

    def __init__(self, url, project, timeout=None):
        self.url = url
        self._timeout = timeout

        self._args = {}
        self.enabled = False
        self.logger = prefect.context.get('logger')

        self._deserializer = self.DESERIALZER(
            ramsis_proj=project.proj_string,
            external_proj=4326,
            ref_easting=0.0,
            ref_northing=0.0,
            transform_func_name='pyproj_transform_to_local_coords')

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

        return bh


class FDSNWSDataSource():
    """
    Fetches seismic event data from a web service.
    """

    DESERIALZER = QuakeMLObservationCatalogDeserializer

    def __init__(self, url, project, timeout=None):
        self.url = url
        self._timeout = timeout

        self._args = {}
        self.enabled = False
        self.logger = prefect.context.get('logger')

        self._deserializer = self.DESERIALZER(
            ramsis_proj=project.proj_string,
            external_proj=4326,
            ref_easting=0.0,
            ref_northing=0.0,
            transform_func_name='pyproj_transform_to_local_coords')

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

        return cat

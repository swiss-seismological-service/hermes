import requests
import logging
import urlparse

from PyQt4 import QtCore
from pymap3d import geodetic2ned

from ramsisdata.forecast import ModelResult, RatePrediction
from ramsisdata.schemas import ForecastSchema


class ModelClient(QtCore.QObject):
    """
    Client for remote induced seismicity model

    :param str model_id: unique id for the model
    :param dict model_config: contains the model configuration
        'url': worker url (including port)
        'parameters': basic model parameters

    """
    # Signal emitted when model results have been retrieved
    finished = QtCore.pyqtSignal(object)

    def __init__(self, model_id, model_config):
        super(ModelClient, self).__init__()
        self.logger = logging.getLogger(__name__)
        self.model_id = model_id
        self.model_config = model_config
        self.url = urlparse.urljoin(model_config['url'], '/run')
        self.poll_interval = 5000  # ms
        self.job_id = None
        self.model = None
        self.model_result = None

    def run(self, scenario, run_info):
        """
        Run the model on the remote worker using the settings specified in
        model_input.

        The worker will return a job ID corresponding to the row ID of the
        final results stored in the remote database.

        :param Scenario scenario: Scenario for which to run the model
        :param dict run_info: Supplementary info for this run:
           'reference_point': (lat, lon, depth) reference for coord. conversion
           'injection_point': (lat, lon, depth) of current injection point

        """
        forecast = scenario.forecast_input.forecast
        forecast_schema = ForecastSchema()
        serialized = forecast_schema.dump(forecast).data
        data = {
            'forecast': serialized,
            'parameters': self.model_config['parameters'],
            'scenario id': scenario.id
        }

        # Add cartesian coordinates
        ref = forecast.forecast_set.project.reference_point
        try:
            catalog = data['forecast']['input']['input_catalog']
            for e in catalog['seismic_events']:
                x, y, z = geodetic2ned(e['lat'], e['lon'], e['depth'],
                                       ref['lat'], ref['lon'], ref['h'])
                e['x'], e['y'], e['z'] = x, y, z

        except TypeError:
            self.logger.info('No seismic events')

        r = requests.post(self.url, json=data, timeout=5)

        if r.status_code == requests.codes.accepted:
            self.logger.info('Model started on worker')
            QtCore.QTimer.singleShot(self.poll_interval, self._get_results)
        elif r.status_code == requests.codes.bad_request:
            self.logger.error('The worker did not accept our input data: {}'
                              .format(r.content))
        elif r.status_code == requests.codes.server_error:
            self.logger.error('The worker reported an error: {}'
                              .format(r.content))
        elif r.status_code == requests.codes.unavailable:
            self.logger.error('The worker did not accept our job: {}'
                              .format(r.content))
        else:
            self.logger.error('Unexpected response received: [{}] {}'
                              .format(r.status_code, r.content))

    def _get_results(self):
        """
        Poll the database periodically until the model results have been
        retrieved, then emit the finished signal.

        """
        r = requests.get(self.url, timeout=5)
        if r.status_code == requests.codes.ok:
            data = r.json()
            if data['status'] == 'complete':
                self.logger.info('Model run completed successfully')
                rate, b_val = data['result']
                model_result = ModelResult()
                model_result.rate_prediction = RatePrediction(rate, b_val, 1)
                # TODO: assign model_result to forecast
            else:
                self.logger.error('Model run failed')
            self.finished.emit(self)
        elif r.status_code == requests.codes.accepted:  # still running
            QtCore.QTimer.singleShot(self.poll_interval, self._get_results)
        elif r.status_code == requests.codes.no_content:
            self.logger.error('The worker has no results and no active job')
        else:
            self.logger.error('The worker reported an error {}'
                              .format(r.status_code))
            # TODO: retry a few times? indefinitely?

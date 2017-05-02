import json
import requests
import logging
import urlparse

from PyQt4 import QtCore

from ramsisdata.schemas import ForecastSchema, ModelResultSchema


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
        forecast_schema = ForecastSchema()
        serialized = forecast_schema.dump(forecast).data
        data = {
            "forecast": serialized,
            "parameters": self.model_config["parameters"]
        }

        r = requests.post(self.url, data={"data": json.dumps(data)})
        try:
            response = json.loads(r.text)
            int(response)
            self.job_id = response
        except ValueError:
            self.logger.error("Job ID not received")
            return

        QtCore.QTimer.singleShot(self.poll_interval, self._get_results)

    def _get_results(self):
        """
        Poll the database periodically until the model results have been
        retrieved, then emit the finished signal.

        """
        r = requests.get(self.url).json()
        if r:
            model_result_schema = ModelResultSchema()
            self.model_result = model_result_schema.load(r).data
            self.finished.emit(self)
        else:
            QtCore.QTimer.singleShot(self.poll_interval, self._get_results)

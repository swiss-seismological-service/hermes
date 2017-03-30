import json
import requests
import logging
import urlparse

from PyQt4 import QtCore

from ramsisdata.schemas import ForecastSchema, ModelResultSchema


class ModelClient(QtCore.QObject):
    # Signal emitted when model results have been retrieved
    finished = QtCore.pyqtSignal(object)

    def __init__(self, model_info):
        super(ModelClient, self).__init__()
        self.logger = logging.getLogger(__name__)
        self.model_info = model_info
        self.url = urlparse.urljoin(model_info['config']['url'], '/run')
        self.poll_interval = 5000  # ms
        self.job_id = None
        self.model = None
        self.model_result = None

    def run(self, forecast):
        """
        Run the model on the remote worker using the settings specified in
        model_input.

        The worker will return a job ID corresponding to the row ID of the
        final results stored in the remote database.

        """
        forecast_schema = ForecastSchema()
        serialized = forecast_schema.dump(forecast).data
        data = {
            "forecast": serialized,
            "parameters": self.model_info["config"]["parameters"]
        }

        r = requests.post(self.url, data={"data": json.dumps(data)})
        response = json.loads(r.text)
        try:
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

import json
import requests
import logging
from datetime import datetime

from PyQt4 import QtCore

from ismodels.common import Model, ModelResult, ModelOutput


class ModelClient(QtCore.QObject):
    # Signal emitted when model results have been retrieved
    finished = QtCore.pyqtSignal(object)

    def __init__(self, model_info, settings):
        super(ModelClient, self).__init__()
        self.logger = logging.getLogger(__name__)
        self.model_info = model_info
        key = 'worker/%s_url' % self.model_info['model']
        key_database = 'worker/%s_database_url' % self.model_info['model']
        self.url = settings.value(key)
        self.url_database = settings.value(key_database)
        self.job_id = None
        self.model = None

    def run(self, model_input):
        """
        Run the model on the remote worker using the settings specified in
        model_input.

        The worker will return a job ID corresponding to the row ID of the
        final results stored in the remote database.

        """
        data = {
            "model_input": model_input.serialize(),
            "parameters": self.model_info["parameters"]
        }

        r = requests.post(self.url, data={"data": json.dumps(data)})
        response = json.loads(r.text)
        try:
            int(response)
            self.job_id = response
        except ValueError:
            self.logger.error("Job ID not received")
            return

        self._get_results()

    def _get_results(self):
        """
        Poll the database periodically until the model results have been
        retrieved, then emit the finished signal.

        """
        headers = {'content-type': 'application/json'}
        params = {'q': json.dumps({
            'filters': [{'name': 'id', 'op': '==', 'val': self.job_id}]
        })}
        r = requests.get(self.url_database, params=params, headers=headers)
        objects = json.loads(r.text)["objects"]

        if objects:
            row = objects[0]
            row["t_run"] = datetime.strptime(row["t_run"], "%Y-%m-%dT%H:%M:%S")

            self.model = Model()
            model_result = ModelResult(row["rate"], row["b_val"], row["prob"])
            model_output = ModelOutput(row["t_run"], row["dt"], self.model)
            model_output.failed = row["failed"]
            model_output.failure_reason = row["failure_reason"]
            model_output.cum_result = model_result
            self.model.output = model_output
            self.model.title = self.model_info['model']

            self.finished.emit(self)

        else:
            seconds = 5
            QtCore.QTimer.singleShot(seconds * 1000, self._get_results)

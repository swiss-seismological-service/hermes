from multiprocessing import Process
import json
import requests

from flask import request
from flask_restful import Resource

from model.common import ModelInput
from model.rj import Rj


class Run(Resource):
    model = None
    url = 'http://localhost:5001'
    url_next_id = url + '/rj/next_job_id'
    url_rj = url + '/rj'

    def post(self):
        data = json.loads(request.form["data"])
        p = Process(target=self._run, args=(data,))
        p.start()

        response = requests.get(self.url_next_id)

    def _run(self, data):
        model_input = ModelInput(None)
        model_input.deserialize(data["model_input"])

        self.model = Rj(**data["parameters"])
        self.model.finished.connect(self._on_model_finished)
        self.model.prepare_run(model_input)
        self.model.run()

    def _on_model_finished(self):
        model_output = self.model.output.serialize()
        data = {"data": json.dumps({"model_output": model_output})}
        requests.post(self.url_rj + '/job1', data)

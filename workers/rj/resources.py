from multiprocessing import Process
import json
import requests

from flask import request
from flask_restful import Resource

from model.common import ModelInput
from model.rj import Rj
from settings import settings


class Run(Resource):
    model = None
    job_id = None

    def post(self):
        headers = {'content-type': 'application/json'}
        params = {'q': json.dumps({
            'limit': 1,
            'order_by': [{'field': 'id', 'direction': 'desc'}]
        })}
        r = requests.get(settings["url_database"], params=params,
                         headers=headers)
        objects = json.loads(r.text)["objects"]
        if objects:
            self.job_id = objects[-1]["id"] + 1
        else:
            self.job_id = 1

        data = json.loads(request.form["data"])
        p = Process(target=self._run, args=(data,))
        p.start()

        return self.job_id

    def _run(self, data):
        model_input = ModelInput(None)
        model_input.deserialize(data["model_input"])

        self.model = Rj(**data["parameters"])
        self.model.finished.connect(self._on_model_finished)
        self.model.prepare_run(model_input)
        self.model.run()

    def _on_model_finished(self):
        model_output = self.model.output.serialize()

        headers = {'content-type': 'application/json'}
        cr = model_output["data"]["cum_result"]
        data = json.dumps({
            "failed": model_output["data"]["failed"],
            "failure_reason": model_output["data"]["failure_reason"],
            "t_run": model_output["data"]["t_run"],
            "dt": model_output["data"]["dt"],
            "rate": cr[0] if cr else "",
            "b_val": cr[1] if cr else "",
            "prob": cr[2] if cr else ""
        })
        requests.post(settings["url_database"], data=data, headers=headers)

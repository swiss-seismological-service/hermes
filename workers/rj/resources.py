from multiprocessing import Process
import json

from flask import request
from flask_restful import Resource

from model.common import ModelInput
from model.rj import Rj


class Run(Resource):
    def post(self):
        data = json.loads(request.form["data"])
        p = Process(target=self._run, args=(data,))
        p.start()

    def _run(self, data):
        model_input = ModelInput(None)
        model_input.deserialize(data["model_input"])

        model = Rj(**data["parameters"])
        model.finished.connect(self._on_model_finished)
        model.prepare_run(model_input)
        model.run()

    def _on_model_finished(self):
        pass

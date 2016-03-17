import json

from flask import request
from flask_restful import Resource

from model.common import ModelOutput


class Rj(Resource):
    def post(self, job_id):
        data = json.loads(request.form["data"])

        model_output = ModelOutput(None, None, None)
        model_output.deserialize(data["model_output"])


class RjId(Resource):
    def get(self):
        pass

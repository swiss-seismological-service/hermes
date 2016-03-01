import json

from flask import request
from flask_restful import Resource

import jobcontrol as jc


class Jobs(Resource):
    def get(self, job_id):
        status = jc.get_status(job_id)
        return status

    def post(self, job_id):
        request_data = json.loads(request.form["data"])
        jc.run(request_data, job_id)

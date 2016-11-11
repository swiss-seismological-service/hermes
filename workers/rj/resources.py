from multiprocessing import Process
import json

from flask import request
from flask_restful import Resource

from data.schemas import ForecastSchema, ModelResultSchema
from model import Rj


class Run(Resource):
    model = None
    output = None

    def post(self):
        """
        Start model run and clear output file.
        Return HTTP status code 200 on success or 500 on failure.

        """
        try:
            self.output = _Persist('output.txt', ModelResultSchema)
            self.output.clear()
            data = json.loads(request.form["data"])
            p = Process(target=self._run, args=(data,))
            p.start()
        except:
            return 500
        return

    def get(self):
        """
        Return results from output file

        """
        result = self.output.get()
        return json.dumps(result)

    def _run(self, data):
        """
        Run the Rj forecast model using the request data provided in *data*

        :param data: request data containing the forecast input and parameters
        :type data: dict

        """
        forecast_schema = ForecastSchema()
        forecast = forecast_schema.load(data["forecast"])
        parameters = data["parameters"]

        self.model = Rj(**parameters)
        self.model.finished.connect(self._on_model_finished)
        self.model.run(forecast)

    def _on_model_finished(self):
        """
        Write model results to output file

        """
        model_result = self.model.model_result
        self.output.write(model_result)


class _Persist:
    """
    Persist SQLAlchemy objects to temporary file

    """
    def __init__(self, filename, schema):
        self.filename = filename
        self.schema = schema

    def write(self, o):
        data = self.schema.dump(o)
        with open(self.filename, 'w') as f:
            f.write(data)

    def get(self):
        with open(self.filename, 'r') as f:
            data = f.readall()
        if data:
            try:
                o = self.schema.load(data)
                return o
            except:
                return None
        else:
            return None

    def clear(self):
        open(self.filename, 'w').close()

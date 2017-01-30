from multiprocessing import Process
import json

from flask import request
from flask_restful import Resource

from ramsisdata.schemas import ForecastSchema, ModelResultSchema
from model import Rj


class Run(Resource):
    def __init__(self):
        self.output = _Persist('output.txt', ModelResultSchema)
        self.model = None

    def post(self):
        """
        Start model run and clear output file.
        Return HTTP status code 200 on success or 500 on failure.

        """
        try:
            self.output.clear()
            data = json.loads(request.form["data"])
            p = Process(target=self._run, args=(data,))
            p.start()
        except:
            return 500
        return 200

    def get(self):
        """
        Return results from output file

        """
        result = self.output.get_serialized()
        return result

    def _run(self, data):
        """
        Run the Rj forecast model using the request data provided in *data*

        :param data: request data containing the forecast input and parameters
        :type data: dict

        """
        forecast_schema = ForecastSchema()
        forecast = forecast_schema.load(data["forecast"])
        forecast = forecast.data
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
    Persist SQLAlchemy objects to a temporary file

    """
    def __init__(self, filename, schema):
        self.filename = filename
        self.schema = schema()

    def write(self, o):
        """ Write SQLAlchemy object to file """
        data = json.dumps(self.schema.dump(o).data)
        with open(self.filename, 'w') as f:
            f.write(data)

    def write_serialized(self, o):
        """ Write serialized object to file """
        data = json.dumps(o)
        with open(self.filename, 'w') as f:
            f.write(data)

    def get(self):
        """ Get SQLAlchemy object from file """
        with open(self.filename, 'r') as f:
            data = f.read()
        if data:
            try:
                o = self.schema.load(json.loads(data))
                return o
            except:
                return None
        else:
            return None

    def get_serialized(self):
        """ Get serialized object from file """
        with open(self.filename, 'r') as f:
            data = f.read()
        if data:
            return json.loads(data)
        else:
            return None

    def clear(self):
        """ Clear the file contents """
        open(self.filename, 'w').close()

from flask import request
from flask import current_app as app
from flask_restful import Resource

from ramsisdata.schemas import ForecastSchema
from .model import Rj

result = None


class Run(Resource):

    def __init__(self):
        self.model = None

    def post(self):
        """
        Start model run and clear output file.
        Return HTTP status code 200 on success or 500 on failure.

        """
        global result
        app.logger.debug('Received post request')
        app.logger.info('Starting model')
        data = request.json
        result = None
        # we run this synchronously since it is such a small calculation
        self._run(data)
        return {'status': 'running'}, 202  # Accepted

    def get(self):
        """
        Return results from output file

        """
        if result is None:
            return '', 204  # No content
        else:
            return {
                'status': 'complete',
                'result': {
                    'rate_prediction': result
                }
            }

    def _run(self, data):
        """
        Run the Rj forecast model using the request data provided in *data*

        :param data: request data containing the forecast input and parameters
        :type data: dict

        """
        global result
        forecast_schema = ForecastSchema()
        try:
            forecast = forecast_schema.load(data['forecast'])
            forecast = forecast.data
        except Exception as e:
            msg = 'Failed to de-serialize data: {}'.format(repr(e))
            app.logger.error(msg)
        parameters = data['parameters']

        self.model = Rj(**data['parameters'])
        result = self.model.run(forecast)


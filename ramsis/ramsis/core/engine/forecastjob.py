import logging

from PyQt4 import QtCore

from job import Job, Stage
from modelclient import ModelClient

from ramsisdata.forecast import ForecastResult


class ISForecastStage(Stage):
    stage_id = 'is_forecast_stage'

    def __init__(self, callback):
        super(ISForecastStage, self).__init__(callback)
        self.active_models = []
        self.clients = []
        self.results = []

    def stage_fun(self):
        forecast = self.inputs['forecast']
        model_config = self.inputs['model_config']

        t_run = forecast.forecast_time
        self._logger.info('Invoking IS forecast stage at t={}.'.format(t_run))

        self._load_models(model_config)
        self.clients = [ModelClient(m) for m in self.active_models]

        for client in self.clients:
            client.finished.connect(self._on_client_run_finished)

        for client in self.clients:
            client.run(forecast)

    def _load_models(self, model_config):

        for model_id, config in model_config.items():
            if config['enabled'] is True:
                self.active_models.append({'model': model_id,
                                           'config': config})

    def _on_client_run_finished(self, client):
        self.results.append(client.model_result)
        self.clients.remove(client)
        if not self.clients:
            self.stage_complete()


class PshaStage(Stage):
    stage_id = 'psha_stage'


class RiskPoeStage(Stage):
    stage_id = 'risk_poe_stage'


class ForecastJob(Job):
    """
    Defines the job of computing forecasts with its three stages

    """
    job_id = 'fc_job'  #: Job ID for ForecastJob
    stages = [ISForecastStage, PshaStage, RiskPoeStage]  #: ForecastJob stages

    # Signals
    forecast_job_complete = QtCore.pyqtSignal()

    def __init__(self, model_config):
        super(ForecastJob, self).__init__()
        self.result = None
        self.model_config = model_config
        self._logger = logging.getLogger(__name__)

    def run_forecast(self, forecast):
        job_input = {
            'forecast': forecast,
            'model_config': self.model_config
        }
        self.stage_completed.connect(self.fc_stage_complete)
        self.result = ForecastResult()
        self.run(job_input)

    def fc_stage_complete(self, stage):
        if stage.stage_id == 'is_forecast_stage':
            self._logger.info('IS forecast stage completed')
            for result in stage.results:
                self.result.model_results[result.model_name] = result
        elif stage.stage_id == 'psha_stage':
            self._logger.info('PSHA stage completed')
            self.result.hazard_oq_calc_id = stage.results['job_id']
        elif stage.stage_id == 'risk_poe_stage':
            self._logger.info('Risk PoE stage completed')
            self.result.risk_oq_calc_id = stage.results['job_id']
        else:
            raise ValueError('Unexpected stage id: {}'.format(stage.stage_id))

        if stage == self.stage_objects[-1]:
            self.forecast_job_complete.emit()

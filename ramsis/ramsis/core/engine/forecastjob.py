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
        settings = self.inputs['settings']

        t_run = forecast.forecast_time
        self._logger.info('Invoking IS forecast stage at t={}.'.format(t_run))

        self.load_models(settings)
        self.clients = [ModelClient(m, settings) for m in self.active_models]

        for client in self.clients:
            client.finished.connect(self._on_client_run_finished)

        for client in self.clients:
            client.run(forecast)

    def load_models(self, settings):
        model_ids = settings.value('ISHA/models')
        load_all = True if 'all' in model_ids else False

        # Reasenberg Jones
        if load_all or 'rj' in model_ids:
            model = {
                'model': 'rj',
                'title': 'Reasenberg-Jones',
                'parameters': {'a': -1.6, 'b': 1.58, 'p': 1.2, 'c': 0.05}
            }
            self.active_models.append(model)

        # ETAS
        if load_all or 'etas' in model_ids:
            model = {
                'model': 'etas',
                'title': 'ETAS',
                'parameters': {'alpha': 0.8, 'k': 8.66, 'p': 1.2, 'c': 0.01,
                               'mu': 12.7, 'cf': 1.98}
            }
            self.active_models.append(model)

        # Shapiro
        # TODO: Re-enable. Temp. disabled bc matlab is not installed on vagrant
        # if load_all or 'shapiro' in model_ids:
        #     model = {
        #         'model': 'shapiro',
        #         'title': 'Shapiro (spatial)',
        #         'parameters': None
        #     }
        #     self.active_models.append(model)

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

    def __init__(self, settings):
        super(ForecastJob, self).__init__()
        self.result = None
        self._settings = settings
        self._logger = logging.getLogger(__name__)

    def run_forecast(self, forecast):
        job_input = {
            'forecast': forecast,
            'settings': self._settings
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

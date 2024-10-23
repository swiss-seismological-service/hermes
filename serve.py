from prefect import serve

from hermes.flows.forecast_handler import forecast_runner
from hermes.flows.modelrun_handler import default_model_runner

if __name__ == '__main__':
    forecast_deployment = forecast_runner.to_deployment(
        name='ForecastRunner')
    modelrun_deployment = default_model_runner.to_deployment(
        name='DefaultModelRunner')
    serve(forecast_deployment, modelrun_deployment)

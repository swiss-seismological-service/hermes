from prefect import serve

from hermes.flows import default_model_runner, forecast_runner
from run import my_flow

if __name__ == '__main__':
    test_flow = my_flow.to_deployment(name="my-flow")
    forecast_deployment = forecast_runner.to_deployment(
        name='ForecastFlowRunner')
    modelrun_deployment = default_model_runner.to_deployment(
        name='DefaultModelFlowRunner')
    serve(forecast_deployment, modelrun_deployment, test_flow)

# Copyright 2019, ETH Zurich - Swiss Seismological Service SED # noqa
"""
Object creation and building facilities.
"""

from sqlalchemy.orm import subqueryload

from ramsis.datamodel.forecast import EStage, ForecastScenario,\
    HazardStage
from ramsis.datamodel.hazard import HazardModelRun, HazardPointValue,\
    HazardMap, HazardCurve
from ramsis.datamodel.status import EStatus

# Seismicity stage: reset the statuses of any model runs with
# a status of error, and set all stages, scenario and forecast to
# pending
# Should this apply to all runs that are not complete?
# If all model runs already completed, (any error runs have been
# disabled) then it resets the stage to complete, scenario, forecast


def reset_seismicity_errors(
        scenario, reset_error=True, reset_dispatched=False,
        reset_complete=False, reset_running=False):
    seismicity_stage = scenario[EStage.SEISMICITY]
    seismicity_model_runs = seismicity_stage.runs
    enabled_model_runs = [run for run in seismicity_model_runs
                          if run.enabled is True]
    for run in enabled_model_runs:
        state = run.status.state
        if state == EStatus.ERROR and reset_error:
            state = EStatus.PENDING
        elif state == EStatus.DISPATCHED and reset_dispatched:
            state = EStatus.PENDING
        elif state == EStatus.COMPLETE and reset_complete:
            state = EStatus.PENDING
        elif state == EStatus.RUNNING and reset_running:
            state = EStatus.PENDING

    run_states = [run.status.state for run in enabled_model_runs]
    if all(state == EStatus.COMPLETE for state in run_states):
        seismicity_stage.status.state = EStatus.COMPLETE
    else:
        seismicity_stage.status.state = EStatus.PENDING

    scenario.status.state = EStatus.PENDING
    scenario.forecast.status.state = EStatus.PENDING

# Hazard stage: If the model runs are in a status of pending,
# delete the model runs and reset stage (and risk stage),
# scenario and forecast to pending
# If the model runs are in status of error, same
# If model runs are in status of prepared, same
# If model runs are completed, same


def reset_stage(scenario_in, store, stage=EStage.HAZARD):
    scenario = store.session.query(ForecastScenario).\
        options(
            # Load models from seismicity stage
            subqueryload(ForecastScenario.stages.of_type(
                HazardStage)).\
            subqueryload(HazardStage.runs).\
            subqueryload(HazardModelRun.hazardmaps).\
            subqueryload(HazardMap.samples).\
            subqueryload(HazardPointValue.geopoint)).\
        options(
            subqueryload(ForecastScenario.stages.of_type(
                HazardStage)).\
            subqueryload(HazardStage.runs).\
            subqueryload(HazardModelRun.hazardcurves).\
            subqueryload(HazardCurve.samples).\
            subqueryload(HazardPointValue.geopoint)).\
        filter(ForecastScenario.id == scenario_in.id).first()
    hazard_stage = scenario[stage]
    hazard_model_runs = hazard_stage.runs
    for run in hazard_model_runs:
        store.delete(run)
    # Deleting all the runs should delete all the results too.
    hazard_stage.status.state = EStatus.PENDING
    scenario.status.state = EStatus.PENDING
    scenario.forecast.status.state = EStatus.PENDING
    store.save()
    store.session.remove()
    return store.get_fresh(scenario_in)

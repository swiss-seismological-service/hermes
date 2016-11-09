# -*- encoding: utf-8 -*-
"""
Wrapper for the spatial shapiro model implemented in matlab by Eszter Kiraly

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import os

import pymatlab
import numpy as np

from common import Model, ModelOutput, ModelResult


class Shapiro(Model):
    """
    Modified Shapiro aftershock forecast model.

    """

    _MATLAB_ERROR_MSG = 'The Shapiro model encountered an error in the ' \
                        'Matlab code. The model inputs that led to the error '\
                        'have been saved to ismodels/model_inputs.mat. To ' \
                        'debug the model load model_inputs.mat file in ' \
                        'matlab and execute shapiro_wrapper.m'
    'directly.'

    def __init__(self):
        """Initializes the model parameters"""
        super(Shapiro, self).__init__()
        self._session = pymatlab.session_factory('-nodisplay -nojvm')

    def _do_run(self):
        """
        Forecast aftershocks at the times given in run data (see prepare_run)
        The model takes the injection flow rate at each forecast time into
        account to compute rates. See super class for how the injection flow
        rate is selected.

        The model forecasts the number of seismic events expected between times
        t given in the run data (see prepare_forecast) and *t + bin_size*.

        Note that any events occurring after the start of each forecast window
        are ignored for the respective forecast.

        """

        # Copy input to matlab workspace
        # We can only pass simple arrays, so we need to decompose our input
        # object here and recompose it in matlab. Prefix all variables with
        # ramsis_ to reduce conflicts
        self._session.run('clear;')
        for name, value in self.model_input.primitive_rep():
            self._session.putvalue('ramsis_' + name, value)
        # Invoke wrapper script
        script_path = os.path.dirname(os.path.realpath(__file__))
        self._session.run('cd ' + script_path)
        try:
            self._session.run("run('shapiro_wrapper.m')")
        except RuntimeError:
            self._session.run("save('model_inputs')")
            self._logger.error(Shapiro._MATLAB_ERROR_MSG)
            if Model.RAISE_ON_ERRORS:
                raise
            else:
                success = False
        else:
            success = self._session.getvalue('forecast_success')

        # Finish up
        t_run = self._model_input.t_run
        dt = self._model_input.t_bin
        output = ModelOutput(t_run=t_run, dt=dt, model=self)
        if success:
            rate = float(self._session.getvalue('forecast_numev'))
            b_val = float(self._session.getvalue('forecast_bval'))
            vol_rates = self._session.getvalue('forecast_vol_rates')
            # TODO: set prob correctly (and the b_vals on vol_results)
            output.cum_result = ModelResult(rate=rate, b_val=b_val, prob=0)
            output.vol_results = [ModelResult(r, 0, 0) for r in vol_rates]
            self._logger.info('number of events: ' + str(rate) +
                              ' voxel max: ' + str(np.amax(vol_rates)))
        else:
            reason = self._session.getvalue('forecast_no_result_reason')
            output.failure_reason = reason
            output.failed = True
            self._logger.info('did not get any results')
        return output

# -*- encoding: utf-8 -*-
"""
Wrapper for the spatial shapiro model implemented in matlab by Eszter Kiraly
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from common import Model, RunResults
import pymatlab
import logging
import os


class Shapiro(Model):
    """
    Modified Shapiro aftershock forecast model.

    """

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
        # atls_ to reduce conflicts
        self._session.run('clear;')
        for name, value in self.run_input.primitive_rep():
            self._session.putvalue('atls_' + name, value)
        # Invoke wrapper script
        script_path = os.path.dirname(os.path.realpath(__file__))
        self._session.run('cd ' + script_path)
        try:
            self._session.run("run('shapiro_wrapper.m')")
        except RuntimeError:
            self._session.run("save('model_inputs')")
            self._logger.error('The Shapiro model encountered an error in the '
                               'Matlab code. The model inputs that led to the '
                               'error have been saved to isha/model_inputs.mat. '
                               'To debug the model load model_inputs.mat file '
                               'in matlab and execute shapiro_wrapper.m '
                               'directly.')
            if (Model.RAISE_ON_ERRORS):
                raise
            else:
                success = False;
        else:
            success = self._session.getvalue('forecast_success')

        # Finish up
        run_results = RunResults(t_run=self._run_input.t_run, model=self)
        if success:
            self._logger.info('number of events: ' + str(num_events))
            run_results.t_results = self._run_input.forecast_times
            run_results.rates = self._session.getvalue('forecast_numev')
        else:
            reason = self._session.getvalue('forecast_no_result_reason')
            run_results.no_result_reason = reason
            run_results.has_results = False
            self._logger.info('did not get any results')
        return run_results

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
        self._logger = logging.getLogger(__name__)
        self._session = pymatlab.session_factory('-nodisplay -nojvm')

    def run(self):
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
        self._logger.info('Model run initiated')

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
        self._session.run("save('model_inputs')")  # Useful for debugging
        self._session.run('who')
        self._session.run("run('shapiro_wrapper.m')")
        print 'shapiro says ' + self._session.buf.value
        # Finish up
        run_results = RunResults(t_run=self._run_input.t_run, model=self)
        run_results.t_results = self._run_input.forecast_times
        self._logger.debug('Model run completed')
        self.finished.emit(run_results)

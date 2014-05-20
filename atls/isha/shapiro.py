# -*- encoding: utf-8 -*-
"""
Wrapper for the spatial shapiro model by Eszter Kiraly

Long Description
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import pymatlab
from common import Model, RunResults
import logging
import numpy as np



class Shapiro(Model):
    """
    Modified Shapiro aftershock forecast model.

    """

    def __init__(self):
        """Initializes the model parameters"""
        super(Shapiro, self).__init__()
        self._logger = logging.getLogger(__name__)
        self._session = pymatlab.session_factory('-nodisplay')


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

        a = np.randn(20,10,30)
        self._session.putvalue('A',a)
        self._session.run('B=2*A')
        b = self._session.getvalue('B')
        print 'shapiro says ' + str(b)

        # Finish up
        run_results = RunResults(t_run=self._run_input.t_run, model=self)
        run_results.t_results = self._run_input.forecast_times

        self._logger.debug('Model run completed')
        self.finished.emit(run_results)

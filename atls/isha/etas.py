# -*- encoding: utf-8 -*-
"""
Modified ETAS Model

The forecast model predicts the rate lambda of events with magnitude M
or larger at time t after a main shock of magnitude Mm as

.. math:: \lambda_m(t) = 10^(alpha(Mm-M)) * K / (t + c)^p

where alpha, K, c and p are empirical constants and M > Mc (magnitude of
completeness).

The total occurrence for a sequence of mainshocks Mi is

.. math:: \lambda(t) = \lambda_0 + \sum \lambda_i(t)

Where the fluid injection is taken into account in the first term as

.. math:: \lambda_0 = \mu + c_f * F_r

mu and c_f are empirical parameters and F_r is the injection flow rate.

By integrating over t, the number of events in the
magnitude range [M1, M2] and time interval [T1, T2] after the main shock
can be computed as

.. math:: \frac{(T_2+c)^{1-p}-(T_1+c)^{1-p}}{1-p} \
          * K * [10^\alpha(M_m-M_1)-10^\alpha(M_m-M_2)] \
          + \mu + c_f * \int_{T_1}^{T_2}F_r(t) dt

which is what this model returns.
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from common import Model, ModelOutput, ForecastResult
import numpy as np
import logging
from datetime import timedelta


class Etas(Model):
    """
    Modified ETAS aftershock forecast model. The model predicts aftershocks
    using a modified background rate that depends on the fluid injection rate.

    The result of the model run is a list of tuples containing for each forecast
    time interval the rate of events in the magnitude range *forecast_mag_range*
    and the probability of one or more events occurring as (rate, probability)

    :ivar alpha: ETAS parameter alpha (productivity)
    :ivar k: Empirical parameter K
    :ivar p: Sequence specific empirical parameter for the Omori-Utsu (1961) law
    :ivar c: Sequence specific empirical parameter for the Omori-Utsu (1961) law
    :ivar m_max: Maximum magnitude
    :ivar m_c: Magnitude of completeness

    """

    def __init__(self, alpha, k, p, c, mu, cf):
        """Initializes the model parameters"""
        super(Etas, self).__init__()
        self.alpha = alpha
        self.k = k
        self.p = p
        self.c = c
        self.mu = mu
        self.cf = cf

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

        # copy everything into local variables for better readability
        a = self.alpha
        k = self.k
        c = self.c
        p = self.p
        mu = self.mu
        cf = self.cf
        events = self._model_input.seismic_events
        hydraulic_events = self._model_input.hydraulic_events
        forecast_times = self._model_input.forecast_times
        t_bin = self._model_input.t_bin
        m_min, m_max = self._model_input.forecast_mag_range
        num_t = len(forecast_times)

        # extract all main shock event magnitudes into a numpy array
        m_all = np.array([e.magnitude for e in events])

        # Compute rate for each forecast time interval
        forecast_rates = np.zeros(num_t)
        for t, i in zip(forecast_times, range(0, num_t)):
            # Convert event times to relative hours for both seismic events
            # and flow
            t_rel = np.array([(t - e.date_time).total_seconds() / 3600.0
                             for e in events])

            # Filter out any events after the start of the forecast interval
            t1 = t_rel[t_rel >= 0]
            t2 = t1 + t_bin
            m = m_all[t_rel >= 0]

            # Compute the integral of lambda(t, M) over the time bin interval
            # and subtract the upper magnitude limit from the lower limit to
            # get the appropriate range
            rate = ((t2+c)**(1-p) - (t1+c)**(1-p)) / (1-p) * \
                k * ((10 ** a*(m-m_min)) - (10 ** a*(m-m_max)))

            # Sum up the contributions from each main shock event
            forecast_rates[i] = rate.sum()

            # Add the modified background activity which is controlled by the
            # fluid injection rate
            flow = self.flow_rate_in_interval(t, t + timedelta(hours=t_bin))
            # FIXME: get the flow units right
            forecast_rates[i] += mu + cf * flow * t_bin

        # Compute the resulting probabilities of one or more events occurring
        probabilities = 1 - np.exp(-forecast_rates)

        # Finish up
        # FIXME: we're only supporting a single forecast now, remove list stuff
        forecast = ForecastResult(rate=forecast_rates[0], prob=probabilities[0])
        output = ModelOutput(t_run=self._model_input.t_run, dt=t_bin, model=self)
        output.result = forecast
        return output

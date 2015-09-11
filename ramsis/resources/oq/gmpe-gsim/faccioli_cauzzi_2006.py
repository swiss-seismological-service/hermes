# The Hazard Library
# Copyright (C) 2014, GEM Foundation
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""
Module exports
:class:`FaccioliCauzzi2006SD001Q200K005`
:class:`FaccioliCauzzi2006SD001Q200K020`
:class:`FaccioliCauzzi2006SD001Q200K040`
:class:`FaccioliCauzzi2006SD001Q200K060`
:class:`FaccioliCauzzi2006SD001Q600K005`
:class:`FaccioliCauzzi2006SD001Q600K020`
:class:`FaccioliCauzzi2006SD001Q600K040`
:class:`FaccioliCauzzi2006SD001Q600K060`
:class:`FaccioliCauzzi2006SD001Q1800K005`
:class:`FaccioliCauzzi2006SD001Q1800K020`
:class:`FaccioliCauzzi2006SD001Q1800K040`
:class:`FaccioliCauzzi2006SD001Q1800K060`
:class:`FaccioliCauzzi2006SD010Q200K005`
:class:`FaccioliCauzzi2006SD010Q200K020`
:class:`FaccioliCauzzi2006SD010Q200K040`
:class:`FaccioliCauzzi2006SD010Q200K060`
:class:`FaccioliCauzzi2006SD010Q600K005`
:class:`FaccioliCauzzi2006SD010Q600K020`
:class:`FaccioliCauzzi2006SD010Q600K040`
:class:`FaccioliCauzzi2006SD010Q600K060`
:class:`FaccioliCauzzi2006SD010Q1800K005`
:class:`FaccioliCauzzi2006SD010Q1800K020`
:class:`FaccioliCauzzi2006SD010Q1800K040`
:class:`FaccioliCauzzi2006SD010Q1800K060`
:class:`FaccioliCauzzi2006SD100Q200K005`
:class:`FaccioliCauzzi2006SD100Q200K020`
:class:`FaccioliCauzzi2006SD100Q200K040`
:class:`FaccioliCauzzi2006SD100Q200K060`
:class:`FaccioliCauzzi2006SD100Q600K005`
:class:`FaccioliCauzzi2006SD100Q600K020`
:class:`FaccioliCauzzi2006SD100Q600K040`
:class:`FaccioliCauzzi2006SD100Q600K060`
:class:`FaccioliCauzzi2006SD100Q1800K005`
:class:`FaccioliCauzzi2006SD100Q1800K020`
:class:`FaccioliCauzzi2006SD100Q1800K040`
:class:`FaccioliCauzzi2006SD100Q1800K060`
"""
from __future__ import division

import numpy as np
from openquake.hazardlib.gsim.base import IPE
from openquake.hazardlib import const
from openquake.hazardlib.imt import MMI, PGV
from openquake.hazardlib.gsim.douglas_stochastic_2013 import \
    DouglasEtAl2013StochasticSD001Q200K005, \
    DouglasEtAl2013StochasticSD001Q200K020, \
    DouglasEtAl2013StochasticSD001Q200K040, \
    DouglasEtAl2013StochasticSD001Q200K060, \
    DouglasEtAl2013StochasticSD001Q600K005, \
    DouglasEtAl2013StochasticSD001Q600K020, \
    DouglasEtAl2013StochasticSD001Q600K040, \
    DouglasEtAl2013StochasticSD001Q600K060, \
    DouglasEtAl2013StochasticSD001Q1800K005, \
    DouglasEtAl2013StochasticSD001Q1800K020, \
    DouglasEtAl2013StochasticSD001Q1800K040, \
    DouglasEtAl2013StochasticSD001Q1800K060, \
    DouglasEtAl2013StochasticSD010Q200K005, \
    DouglasEtAl2013StochasticSD010Q200K020, \
    DouglasEtAl2013StochasticSD010Q200K040, \
    DouglasEtAl2013StochasticSD010Q200K060, \
    DouglasEtAl2013StochasticSD010Q600K005, \
    DouglasEtAl2013StochasticSD010Q600K020, \
    DouglasEtAl2013StochasticSD010Q600K040, \
    DouglasEtAl2013StochasticSD010Q600K060, \
    DouglasEtAl2013StochasticSD010Q1800K005, \
    DouglasEtAl2013StochasticSD010Q1800K020, \
    DouglasEtAl2013StochasticSD010Q1800K040, \
    DouglasEtAl2013StochasticSD010Q1800K060, \
    DouglasEtAl2013StochasticSD100Q200K005, \
    DouglasEtAl2013StochasticSD100Q200K020, \
    DouglasEtAl2013StochasticSD100Q200K040, \
    DouglasEtAl2013StochasticSD100Q200K060, \
    DouglasEtAl2013StochasticSD100Q600K005, \
    DouglasEtAl2013StochasticSD100Q600K020, \
    DouglasEtAl2013StochasticSD100Q600K040, \
    DouglasEtAl2013StochasticSD100Q600K060, \
    DouglasEtAl2013StochasticSD100Q1800K005, \
    DouglasEtAl2013StochasticSD100Q1800K020, \
    DouglasEtAl2013StochasticSD100Q1800K040, \
    DouglasEtAl2013StochasticSD100Q1800K060


class FaccioliCauzzi2006SD001Q200K005(IPE):
    """
    Implements the GMICE by Faccioli & Cauzzi which converts ground velocities
    to EMS-98 intensities:

    Faccioli, E., Cauzzi, C. (2006) "Macroseismic intensities for seismic
        scenarios, estimated from instrumentally based correlations"
        First European Conference on Earthquake Engeneering and Seismology,
        Geneva, p.569

    In this implementation the GMPE of Douglas et al. (2013) for geothermal
    environments are used to compute PGV.
    TODO: can't we pass parameters to __init__()? That would allow us to choose
    the base GMPE (and maybe also base GMPE parameters like stress drop etc.)

    The stochastic model by Douglas et al. (2013) provides coefficients for
    36 GMPEs, corresponding to different values of Stress Drop (1 bar, 10 bar,
    100 bar), Attentuation Quality Factor Q (200, 600, 1800) and high-frequency
    Kappa (0.005, 0.02, 0.04, 0.05 s).

    The present model is implemented for Stress Drop 1 bar, Q 200 and
    Kappa 0.005 s.

    The models for each combination of Stress Drop, Q and Kappa
    are implemented in subclasses, with only the median coefficients modified
    in each subclass


    Notes on implementation:

        1) Felt intensities on soils are corrected by +0.47 in based on
           Faeh, D., Kaestli, P., Alvarez, S., Poggi, V. (2010) "Intensity
           data from the MECOS database" Schweizerischer Erdbebendienst ETH
           Zuric, Report SED/PRP/R/012/20100607

    """
    #: The supported tectonic region type is Geothermal because
    #: the equations have been developed for geothermal regions
    DEFINED_FOR_TECTONIC_REGION_TYPE = const.TRT.GEOTHERMAL

    #: The supported intensity measure types are PGA, PGV, and SA, see table
    #: 4.a, pages 22-23
    DEFINED_FOR_INTENSITY_MEASURE_TYPES = set([
        MMI
    ])

    #: The supported intensity measure component is 'average horizontal', see
    #: section entitiled "Empirical Analysis", paragraph 1
    DEFINED_FOR_INTENSITY_MEASURE_COMPONENT = const.IMC.AVERAGE_HORIZONTAL

    #: The supported standard deviations are total, inter and intra event, see
    #: table 4.a, pages 22-23
    DEFINED_FOR_STANDARD_DEVIATION_TYPES = set([
        const.StdDev.INTER_EVENT,
        const.StdDev.INTRA_EVENT,
        const.StdDev.TOTAL
    ])

    #: Required site parameter is only Vs30 (used to distinguish rock
    #: and deep soils), see paragraph 'On functional forms', page 463.
    REQUIRES_SITES_PARAMETERS = set(('vs30', ))

    #: The required rupture parameters are magnitude
    REQUIRES_RUPTURE_PARAMETERS = set(('mag',))

    #: The required distance parameter is hypocentral distance
    REQUIRES_DISTANCES = set(('rhypo',))

    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD001Q200K005()

    def get_mean_and_stddevs(self, sites, rup, dists, imt, stddev_types):
        gmpe_imt = PGV()
        mean, std_devs = self._gmpe.get_mean_and_stddevs(sites, rup, dists,
                                                         gmpe_imt,
                                                         stddev_types)

        # convert to intensity according to Kaestli & Faeh (2006)
        soil_correction = np.zeros_like(sites.vs30)
        # correct felt intensities on soft soils
        soil_correction[sites.vs30 > 0] = .47
        # mean comes back in log(cm/s). convert to m/s
        mean = np.exp(mean) / 100.
        mean_mmi = 1.8 * np.log10(mean) + 8.69 + soil_correction

        # use constant sigma of 0.71 for GMICE
        std_devs = np.hypot(std_devs, 0.71)

        return mean_mmi, std_devs


class FaccioliCauzzi2006SD001Q200K020(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 001 - Q 200 - Kappa 0.02
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD001Q200K020()


class FaccioliCauzzi2006SD001Q200K040(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 001 - Q 200 - Kappa 0.04
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD001Q200K040()


class FaccioliCauzzi2006SD001Q200K060(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 001 - Q 200 - Kappa 0.06
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD001Q200K060()


class FaccioliCauzzi2006SD001Q600K005(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 001 - Q 600 - Kappa 0.005
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD001Q600K005()


class FaccioliCauzzi2006SD001Q600K020(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 001 - Q 600 - Kappa 0.020
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD001Q600K020()


class FaccioliCauzzi2006SD001Q600K040(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 001 - Q 600 - Kappa 0.040
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD001Q600K040()


class FaccioliCauzzi2006SD001Q600K060(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 001 - Q 600 - Kappa 0.060
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD001Q600K060()


class FaccioliCauzzi2006SD001Q1800K005(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 001 - Q 1800 - Kappa 0.005
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD001Q1800K005()


class FaccioliCauzzi2006SD001Q1800K020(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 001 - Q 1800 - Kappa 0.020
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD001Q1800K020()


class FaccioliCauzzi2006SD001Q1800K040(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 001 - Q 1800 - Kappa 0.040
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD001Q1800K040()


class FaccioliCauzzi2006SD001Q1800K060(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 001 - Q 1800 - Kappa 0.060
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD001Q1800K060()


class FaccioliCauzzi2006SD010Q200K005(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 010 - Q 200 - Kappa 0.005
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD010Q200K005()


class FaccioliCauzzi2006SD010Q200K020(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 010 - Q 200 - Kappa 0.020
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD010Q200K020()


class FaccioliCauzzi2006SD010Q200K040(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 010 - Q 200 - Kappa 0.040
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD010Q200K040()


class FaccioliCauzzi2006SD010Q200K060(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 010 - Q 200 - Kappa 0.060
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD010Q200K060()


class FaccioliCauzzi2006SD010Q600K005(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 010 - Q 600 - Kappa 0.005
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD010Q600K005()


class FaccioliCauzzi2006SD010Q600K020(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 010 - Q 600 - Kappa 0.02
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD010Q600K020()


class FaccioliCauzzi2006SD010Q600K040(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 010 - Q 600 - Kappa 0.04
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD010Q600K040()


class FaccioliCauzzi2006SD010Q600K060(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 010 - Q 600 - Kappa 0.06
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD010Q600K060()


class FaccioliCauzzi2006SD010Q1800K005(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 010 - Q 600 - Kappa 0.005
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD010Q1800K005()


class FaccioliCauzzi2006SD010Q1800K020(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 010 - Q 1800 - Kappa 0.02
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD010Q1800K020()


class FaccioliCauzzi2006SD010Q1800K040(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 010 - Q 1800 - Kappa 0.04
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD010Q1800K040()


class FaccioliCauzzi2006SD010Q1800K060(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 010 - Q 1800 - Kappa 0.06
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD010Q1800K060()


class FaccioliCauzzi2006SD100Q200K005(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 100 - Q 200 - Kappa 0.005
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD100Q200K005()


class FaccioliCauzzi2006SD100Q200K020(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 100 - Q 200 - Kappa 0.02
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD100Q200K020()


class FaccioliCauzzi2006SD100Q200K040(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 100 - Q 200 - Kappa 0.04
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD100Q200K040()


class FaccioliCauzzi2006SD100Q200K060(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 100 - Q 200 - Kappa 0.06
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD100Q200K060()


class FaccioliCauzzi2006SD100Q600K005(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 100 - Q 600 - Kappa 0.005
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD100Q600K005()


class FaccioliCauzzi2006SD100Q600K020(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 100 - Q 600 - Kappa 0.02
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD100Q600K020()


class FaccioliCauzzi2006SD100Q600K040(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 100 - Q 600 - Kappa 0.04
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD100Q600K040()


class FaccioliCauzzi2006SD100Q600K060(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 100 - Q 600 - Kappa 0.06
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD100Q600K060()


class FaccioliCauzzi2006SD100Q1800K005(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 100 - Q 1800 - Kappa 0.005
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD100Q1800K005()


class FaccioliCauzzi2006SD100Q1800K020(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 100 - Q 1800 - Kappa 0.02
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD100Q1800K020()


class FaccioliCauzzi2006SD100Q1800K040(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 100 - Q 1800 - Kappa 0.04
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD100Q1800K040()


class FaccioliCauzzi2006SD100Q1800K060(
        FaccioliCauzzi2006SD001Q200K005):
    """
    Stress Drop 100 - Q 1800 - Kappa 0.04
    """
    def __init__(self):
        self._gmpe = DouglasEtAl2013StochasticSD100Q1800K060()

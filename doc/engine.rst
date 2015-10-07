Forecast Engine
================

The forecast engine runs forecasts when the forecast task (see Scheduler in :doc:`core`) invokes the *run_forecast()* method. It sets up a *ForecastJob* that has three stages for

1. The forecasting of induced seismicity
2. The computation of hazard
3. The computation of risk

The ``ForecastJob`` automatically passes the results from each stage as the input to the next stage. The engine subscribes to the ``stage_completed`` signal that :class:`~core.job.Job` emits to collect the results from each stage and store them in the :doc:`Project's <project>` forecast history.

The hazard and risk computations are performed by `OpenQuake <http://www.globalquakemodel.org/openquake/about/>`_ which maintains its own database for results. The forecast result history thus only stores a reference the OpenQuake results for stages 2 and 3.

The following sections describe the individual stages in more detail.


Induced Seismicity Forecasting
------------------------------

Induced seismicity ("IS") forecasts are computed by multiple competing models. Some of them are simple statistical models that are implemented in a few lines of code, while others are sophisticated physical-stochastic models, that run for long periods of time on multiple CPU cores. In addition, some of the models are not implemented in python and run in MATLAB environment or even on an external cluster. 

The individual *IS* models are run by the :class:`~core.isforecaster.ISForecaster` and the :mod:`core.ismodelcontrol` module. The latter loads all the models when the software launches and runs them in parallel when *run_active_models(model_input)* is invoked by ``ISForecaster``. The ``ISForecaster`` also keeps track of progress and collects the results from each model when they're done.


Hazard and Risk Computation
---------------------------

The hazard and risk computation are performed externally by OpenQuake (OQ). The modules in the :doc:`modules/core.oq` provide the interface classes to start OQs own engine and to collect the results when the computation is done.
OpenQuake reads some of its inputs from .xml files. The input files are generated on the fly by :mod:`core.oq.controller`.

.. figure:: images/engine_clsd.png
   :align: center

   Classes controlled by Engine to perform forecasts and hazard/risk computations.
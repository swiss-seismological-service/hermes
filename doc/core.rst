Core
====

The RT-RAMSIS :doc:`modules/core` contains the business logic of RT-RAMSIS. Its top level module is :mod:`~core.controller` with the :class:`~core.controller.Controller` class, which controls most of the components that make up the core and also serves as the entry point for the user interface.

The class diagram below shows the main component and the attributes and methods that are important when the software is running forecasts.

.. figure:: images/core_clsd.png
   :align: center

   Class diagram of the RT-RAMSIS core.

While the :class:`~core.controller.Controller` class coordinates between the core objects, it is the ``Engine`` that does the actual work of computing forecasts.

Engine
------

.. py:currentmodule:: core.engine

The :doc:`engine` (Class :class:`Engine`) is responsible for running the actual forecasts. It is invoked by the forecast task through ``run_forecast()``. When ``run_forecast()`` is invoked, the engine will setup a new :class:`~core.ramsisjob.ForecastJob` with the input data that is relevant for this particular run. A ``ForecastJob`` in turn consists of multiple :class:`Stages <core.job.Stage>` (rate forecasting, hazard computation, risk computation). The engine acts as the delegate for the ``ForecastJob`` by processing intermediate results and passing data between the individual stages of the job.

Completion of a forecast is reported to the framework by emitting the ``forecast_complete`` signal to the rest of the application.

Forecast Stages
^^^^^^^^^^^^^^^

IS Rate Forecasting
"""""""""""""""""""

.. py:currentmodule:: core.ismodels.common

The basis for each forecast job are the induced seismicity rate forecasting models. When invoked, the framework passes the seismic and the hydraulic history to :class:`Model` as input. The model then computes a forecast for the expected rate of seismicity in the near future. The result, a synthetic earthquake catalog, is passed to the next stage.

The common interface for IS models is defined and documented in the :mod:`core.ismodels.common` module.

Executing the IS rate forecasting stage is a relatively complex task, since there are potentially many different models that need to run in parallel. Some models consist of a few lines of code and run in milliseconds while others are far more complex and may run on an external machine for minutes or even hours. In addition, not all models might be active all the time. The user might decide to activate just one or two models for testing a specific scenario.

The :class:`~core.ramsisjob.ISForecastStage` thus works with two helpers that each handle a part of the complexity:

* The :class:`~core.isforecaster.ISForecaster` keeps track of the state of each individual model when they run and emits a signal to the framework when all models have completed.
* The module :mod:`core.ismodelcontrol` defines a singleton which is responsible for loading all active IS models when the program starts and running them in parallel when ``run_active_models()`` is called. It is the :class:`~core.isforecaster.ISForecaster` that calls this method during a regular forecast job. The ``ismodelcontrol`` module makes sure that each model runs in a seperate thread so that they don't block the user interface.

Hazard Computation
""""""""""""""""""

After a synthetic catalog has been computed by the IS forecast stage, the hazard stage (also Probabilistic Seismic Hazard Assessment or "PSHA") is invoked. RT-RAMSIS relies on the `OpenQuake Framework <http://www.globalquakemodel.org/openquake/about/>`_ by GEM to do hazard and risk computations. The module :mod:`core.oq.controller` provides the interface for RT-RAMSIS to interact with OpenQuake directly.


Scheduler
---------

.. py:currentmodule:: scheduler.taskscheduler

The :class:`TaskScheduler` keeps a list of :class:`ScheduledTasks <ScheduledTask>` that it runs at specific absolute times (one-off tasks) or relative time intervals (repeating tasks). For example, one of the most central tasks is the task that initiates a new forecast every six hours (or whatever time interval is configured in the app's settings). When it is time to execute the forecast task, the ``run_forecast()`` method in :class:`~core.engine.Engine` will be invoked by the forecast task.

It is important to note the tasks themselves do not do any work at all. In fact, ``ScheduledTask`` has only three properties: a name, the time that defines when the task should execute, and a reference to an external method it should call.

.. py:currentmodule:: data.project.ramsisproject

Also note, that the scheduler does not work with the current local system time. Instead it only reacts to changes on the current ``project_time`` which is a property of ``Project``. In real time operation, ``project_time`` and the current system time are the same. However, when the software operates in simulation mode, ``project_time`` is updated by the ``simulator`` and can thus run faster or slower than the system time, depending on the configured simulation speed.


Project
-------

``Project`` (implemented in :class:`Project`) contains all the relevant data for the currently active project, such as the history of seismic event, hydraulic events, forecast results and project specific settings.

The current ``project_time`` (a property of project) serves as the basis for all scheduled activity of the core.


Simulator
---------

The :class:`~simulator.Simulator` is only used for testing or scientific experiments where the user wants to reprocess existing data. All that the simulator does, is advance the ``project_time`` in regular intervals by calling ``update_project_time()`` on the ``project``. The simulator's ``speed`` setting governs how much time passes with each update.

The simulator can also be configured to update ``project_time`` based on an external signal instead of working with regular intervals. When the simulator is configured to run in "infinite speed" for example, it will listen to the ``forecast_complete`` signal that is emitted by the ``engine`` and immediately advance ``project_time`` to the time of the next forecast. This effectively results in forecasts being run as fast as the computational power of the computer allows.




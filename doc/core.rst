Core
====

The RT-RAMSIS **core** package contains the business logic of RT-RAMSIS. It's
top level module is **controller** which controls most of the components that
make up the core and also serves as the entry point for the user interface.

The class diagram below shows the main component and the attributes and methods that are important when the software is running forecasts.

.. figure:: images/core_clsd.png
   :align: center

   Class diagram of the RT-RAMSIS core.


Scheduler
---------

The scheduler keeps a list of **tasks** that it runs at specific absolute times (one-off tasks) or relative time intervals (repeating tasks). For example, one of the most central tasks is the task that initiates a new forecast every six hours (or whatever time interval is configured in the app's settings). When it is time to execute the forecast task, the *engine's* *run_forecast()* method will be invoked by the forecast task.

It is important to note the the tasks themselves do not do any work at all. In fact, :class:Task has only three properties: a name, the time that defines when the task should execute, and a reference to an external method it should call.

Also note, that the scheduler does not work with the current local system time. Instead it only reacts to changes on the current *project_time* which is a property of *project*. In real time operation, *project_time* and the current system time are the same. However, when the software operates in simulation mode, *project_time* is updated by the *simulator* and can thus run faster or slower than the system time, depending on the configured simulation speed.


Project
-------

:doc:`Project <project>` contains all the relevant data for the currently active project, such as the history of seismic event, hydraulic events, forecast results and project specific settings.

The current *project_time* (a property of project) serves as the basis for all scheduled activity of the core.


Simulator
---------

The *Simulator* is only used for testing or scientific experiments where the user wants to reprocess existing data. All that the simulator does, is advance the *project_time* in regular intervals by calling *update_project_time()* on the *project*. The simulator's *speed* setting governs how much time passes with each update.

The simulator can also be configured to update *project_time* based on an external signal instead of working with regular intervals. When the simulator is configured to run in "infinite speed" for example, it will listen to the *forecast_complete* signal that is emitted by the *engine* and immediately advance *project_time* to the time of the next forecast. This effectively results in forecasts being run as fast as the computational power of the computer allows.


Engine
------

The :doc:`engine` is responsible for running the actual forecasts. It is invoked by the forecast task through *run_forecast*. When *run_forecast* is invoked, the engine will setup a new *ForecastJob* with the input data that is relevant for this particular run. A *ForecastJob* consists of multiple stages (rate forecasting, hazard computation, risk computation). The engine acts as the delegate for the *ForecastJob* by processing intermediate results and passing data between the individual stages of the job.

It reports completion of a forecast by emitting the *forecast_complete* signal to the rest of the application.

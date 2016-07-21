Project
=======

The :class:`~data.project.project.Project` maintains the data that is relevant for the project. This is mainly the seismic history, the hydraulic history and the forecasting results.

Project data is loaded and stored from an .sqlite file which is an sqlite database. The content of the database is mapped to python objects through the third party ORM library `sqlalchemy <http://docs.sqlalchemy.org/en/rel_1_0/>`_. For more information on the persistence stack, refer to the last section on this page.


Project Time
------------

In addition to the data, the project also keeps the current time in the ``project_time`` attribute. ``project_time`` is updated externally through the ``update_project_time()`` method. The :class:`~scheduler.taskscheduler.TaskScheduler` runs Tasks based on the current ``project_time``.


Project Data and the Persistence Stack
--------------------------------------

Time related project data is stored in event histories, e.g. :class:`~data.seismiceventhistory.SeismicCatalog` for seismic events and :class:`~data.forecasthistory.ForecastSet` for seismicity forecasting results. Several layers of abstraction are used to persist data as shown in the diagram below.

.. figure:: images/project_clsd.png
   :align: center

   Project and persistence stack. Note that not all history classes are shown.

The :class:`~data.project.store.Store` manages the various components that are used to operate *sqlalchemy* such as the database engine, the session and the data model. It provides convenience methods to load, delete and store data to and from the database.

The store is injected to the project by the ramsis :class:`~core.controller.Controller` when the project loads. Application components typically only access event histories and don't interact with the store directly.
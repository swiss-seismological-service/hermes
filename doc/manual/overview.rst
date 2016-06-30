Overview
========

This chapter gives a broad overview of the architecture of RT-RAMSIS. It describes the most important modules and how they interact with each other.

RT-RAMSIS is built on **Qt**, a popular and very capable application framework.Qt provides basic application functionality such as a GUI framework, messaging (signals and slots) and a run loop for event processing.

RT-RAMSIS Architecture
----------------------

On the top level RT-RAMSIS implements a model view controller (`MVC <https://en.wikipedia.org/wiki/Model–view–controller>`_) controller architecture, which separates the business logic (*Model*) from the GUI (*View*) through a *Controller*. In fact the GUI is entirely optional, and can be easily replaced by something else, e.g. a command line or web interface.

The *Controller* passes user actions from the *View* to the *Model*. To update *Views* when the *Model* has new data available, the *Controller* subscribes to *signals* provided by the Model objects. By using *signals* and *slots* we ensure loose coupling between the core logic and GUI, the core logic is not aware of the GUI at all.

The figure :ref:`ramsis-architecture` below shows the main components of RT-RAMSIS.

.. _ramsis-architecture:
.. figure:: images/ramsis_architecture.svg
   :align: center

   Block diagram of RT-RAMSIS. 

Note that *Controller* is not an actual object in RT-RAMSIS but rather a collection of window controller classes named xxx\ *window.py*. The name *Controller* is used in the diagram above in a conceptual sense. In RT-RAMSIS there is also a ``Controller`` **class** which is actually part of the core. 

The window and view controllers interact directly with the core, while the core sends updates to the GUI via Qt signals. The forecast engine is responsible for running forecast jobs when the scheduler tells it to. Jobs consist of multiple Stages that run in succession. 

.. automodule:: core
   :members:

Source Code Organisation
------------------------

The source code directory organizes the components shown above as follows

* **ui** contains the the :doc:`user interface <user_interface>` files, i.e. the GUI elements and their respective controllers. All view/window controllers are named xxx\ *window.py*. Qt generated user interface files are stored in *ui/views*. Some of the more complex views have their own `view models <https://en.wikipedia.org/wiki/Model_View_ViewModel>`_ to hold data in a view specific manner. These are stored under **ui/viewmodels**.
* **core** The :doc:`core` package contains most of the business logic of RT-RAMSIS. Its main module defines the ``Controller``: class which owns the main components of RT-RAMSIS and serves as the entry point for the user interface actions. ``Controller`` controls the forecasting :doc:`engine`, the :doc:`scheduler` and the :doc:`simulator`. It also manages the currently active :doc:`project`.

  The two sub-packages **core/oq** and **core/ismodels** contain the modules for interfacing with openquake and for running induced seismicity forecasting models respectively.

The other top level packages and files are

* **data** contains the :doc:`project` and the domain model objects that store project data (seismic events, hydraulic events, forecasting results etc.)
* **resources** contains static files such as configuration files for open quake etc.
* **doc** contains the files to build this documentation
* **main.py** is responsible for launching the application and for setting up the logging facilities etc.
* **ramsis.py** contains the application object, handles application wide settings and connects the GUI with the core logic.

The diagram below shows the class relationships for the main components and packages as listed above. A complete class diagram is available :download:`here <images/overviewdetailed_clsd.png>`.

.. figure:: images/overview_clsd.png
   :align: center

   Class diagram of the main components in RT-RAMSIS



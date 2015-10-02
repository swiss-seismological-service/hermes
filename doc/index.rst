.. RAMSIS documentation master file, created by
   sphinx-quickstart on Wed Aug  7 16:11:09 2013.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

#################################
RT-RAMSIS Developer Documentation
#################################

RT-RAMSIS is an adaptive traffic light system for induced seismicity. This
documentation describes the top level concepts of the software's architecture
and the APIs of all important modules.

This documentation can be created by running ``make html`` from the **doc**
directory. 

.. note:: This documentation is still work in progress. Some sections might be incomplete or outdated. You're encouraged to fix the docs where necessary. 


.. toctree::
   :maxdepth: 1
   :caption: Concepts

   overview
   core
   project
   engine
   user_interface

.. toctree::
   :maxdepth: 2
   :caption: Main Packages

   modules/core.rst
   modules/data.rst
   modules/ui.rst

.. toctree::
   :maxdepth: 2
   :caption: Additional Modules

   modules/eqstats.rst
   modules/eventimporter.rst
   modules/ramsis.rst
   modules/ramsissettings.rst
   modules/scheduler.rst
   modules/simulator.rst
   modules/tools.rst



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


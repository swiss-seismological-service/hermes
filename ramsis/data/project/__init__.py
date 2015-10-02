# -*- encoding: utf-8 -*-
# Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""
Classes to store and persist project related data.

A `RamsisProject` consists of several `EventHistories <EventHistory>` to store
seismic and hydraulic data as well as the results of forecasts.

The `Store` class acts as the interface between the in-memory data classes
and the `sqlalchemy` persistence stack.

Refer to the :doc:`/project` documentation for more conceptual information
related to this package.

"""

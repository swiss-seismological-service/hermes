# -*- encoding: utf-8 -*-
"""
ATLS hazard and risk computation module

The ATLS hazard and risk module is a wrapper around openquake.
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from PyQt4 import QtCore


hazard_complete = QtCore.pyqtSignal(object)
risk_complete = QtCore.pyqtSignal(object)


def run_hazard():
    pass

def run_risk():
    pass
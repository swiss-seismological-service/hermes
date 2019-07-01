# Copyright (C) 2019, ETH Zurich - Swiss Seismological Service SED
"""
UI visual style definitions

"""
import enum


class StatusColor(enum.Enum):
    """ Defines colors for status messages """
    PENDING = '#0099CC'
    COMPLETE = '#00CC99'
    DISABLED = '#D0D0D0'
    ERROR = '#FF470A'
    RUNNING = '#9900CC'
    OTHER = '#F8E81C'

# -*- encoding: utf-8 -*-
"""
Generic notifications for http clients

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""


class ClientNotification(object):
    RUNNING = 'Running'
    COMPLETE = 'Complete'
    ERROR = 'Error'
    OTHER = 'Other'

    def __init__(self, state, calc_id=None, response=None):
        self.calc_id = calc_id
        self.state = state
        self.response = response


class RunningNotification(ClientNotification):
    def __init__(self, calc_id, response=None):
        super(RunningNotification, self).\
            __init__(self.RUNNING, calc_id, response)


class ErrorNotification(ClientNotification):
    def __init__(self, calc_id=None, response=None):
        super(ErrorNotification, self).\
            __init__(self.ERROR, calc_id, response)


class CompleteNotification(ClientNotification):
    def __init__(self, calc_id, response=None):
        super(CompleteNotification, self).\
            __init__(self.COMPLETE, calc_id, response)


class OtherNotification(ClientNotification):
    def __init__(self, calc_id=None, response=None):
        super(OtherNotification, self).\
            __init__(self.OTHER, calc_id, response)

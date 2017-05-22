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

    def __init__(self, state, calc_id=None, response=None, model_result=None):
        self.calc_id = calc_id
        self.state = state
        self.response = response
        self.model_result = model_result


class RunningNotification(ClientNotification):
    def __init__(self, calc_id, response=None, model_result=None):
        super(RunningNotification, self).\
            __init__(self.RUNNING, calc_id, response, model_result)


class ErrorNotification(ClientNotification):
    def __init__(self, calc_id=None, response=None, model_result=None):
        super(ErrorNotification, self).\
            __init__(self.ERROR, calc_id, response, model_result)


class CompleteNotification(ClientNotification):
    def __init__(self, calc_id, response=None, model_result=None):
        super(CompleteNotification, self).\
            __init__(self.COMPLETE, calc_id, response, model_result)


class OtherNotification(ClientNotification):
    def __init__(self, calc_id=None, response=None, model_result=None):
        super(OtherNotification, self).\
            __init__(self.OTHER, calc_id, response, model_result)

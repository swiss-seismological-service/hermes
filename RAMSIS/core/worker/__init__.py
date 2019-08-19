# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Worker related *RT-RAMSIS* facilities.
"""

import abc
import enum
import logging


from ramsis.utils.error import Error


class WorkerError(Error):
    """Base worker error ({})."""


class EWorkerHandle(enum.Enum):
    SFM_REMOTE = enum.auto()


class WorkerHandleBase(abc.ABC):
    """
    Interface simplifying the communication with *RT-RAMSIS* model worker
    implementations. Concrete implementations of :py:class:`WorkerHandleBase`
    are intended to encapsulate scientific models.
    """
    MODEL_ID = None

    LOGGER = 'ramsis.core.worker_handle'

    class WorkerHandleError(WorkerError):
        """Base worker handle error ({})."""

    def __init__(self, **kwargs):
        self.logger = logging.getLogger(
            kwargs.get('logger') if kwargs.get('logger') else self.LOGGER)

    @classmethod
    def create(cls, handle_id, **kwargs):
        """
        Factory method for worker handle creation

        :param handle_id: Handle identifier
        :type: :py:class:`EWorkerHandle`
        :param kwargs: Keyword value parameters passed to the underlying
            worker handle constructor

        :returns: Instance of a concrete implementation of
            :py:class:`WorkerHandleBase`
        :rtype: :py:class:`WorkerHandleBase`
        """
        if EWorkerHandle.SFM_REMOTE == handle_id:
            return RemoteSeismicityWorkerHandle(**kwargs)

        raise cls.WorkerHandleError(
            'Invalid handle identifier: {!r}'.format(handle_id))

    @classmethod
    def create_payload(cls, handle_id, **kwargs):
        """
        Factory method for worker handle payload creation

        :param handle_id: Handle identifier
        :type: :py:class:`EWorkerHandle`
        :param kwargs: Keyword value parameters passed to the underlying
            worker handle payload constructor
        """
        # TODO(damb): Guarantee that that WorkerHandle.Payload is implemented.
        if EWorkerHandle.SFM_REMOTE == handle_id:
            return RemoteSeismicityWorkerHandle.Payload(**kwargs)

        raise cls.WorkerHandleError(
            'Invalid handle identifier: {!r}'.format(handle_id))

    @property
    @abc.abstractmethod
    def model(self):
        pass

    @abc.abstractmethod
    def query(self, task_ids=[]):
        pass

    @abc.abstractmethod
    def compute(self, payload, **kwargs):
        pass

    @abc.abstractmethod
    def delete(self, task_ids=[]):
        pass


WorkerHandle = WorkerHandleBase

# avoid circular imports
from RAMSIS.core.worker.sfm import RemoteSeismicityWorkerHandle  # noqa

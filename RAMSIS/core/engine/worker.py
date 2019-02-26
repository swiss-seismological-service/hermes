# This is <worker.py>
# -----------------------------------------------------------------------------
#
# Copyright (c) 2018 by Daniel Armbruster (SED, ETHZ)
#
#
# REVISION and CHANGES:
# 2018/10/23
#
# =============================================================================
"""
Worker related *RT-RAMSIS* facilities.
"""

import abc
import collections
import logging
import requests
import uuid

import marshmallow

from urllib.parse import urlparse
from marshmallow import Schema, fields
from marshmallow.validate import OneOf

from ramsis.utils.error import Error
from ramsis.utils.protocol import (SFMWorkerInputMessageSchema, StatusCode,
                                   MIMETYPE)


class FilterSchema(Schema):

    status = fields.Str(
        validate=OneOf(choices=[c.name for c in StatusCode],
                       error=('Invalid status given: (input={input}, '
                              'choices={choices}.')))
    status_code = fields.Int(
        validate=OneOf(choices=[c.value for c in StatusCode],
                       error=('Invalid status given: (input={input}, '
                              'choices={choices}.')))

# class FilterSchema


class WorkerHandleBase(abc.ABC):
    """
    Interface simplifying the communication with *RT-RAMSIS* model worker
    implementations. Concrete implementations of :py:class:`WorkerHandleBase`
    are intended to encapsulate scientific models.
    """
    MODEL_ID = None

    LOGGER = 'ramsis.core.worker_handle'

    class WorkerHandleError(Error):
        """Base worker handle error ({})."""

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

# class WorkerHandleBase


# -----------------------------------------------------------------------------
class RemoteSeismicityWorkerHandle(WorkerHandleBase):
    """
    Base class simplifying the communication with *RT-RAMSIS* remote seismicity
    forecast model worker implementations (i.e. webservice implementations of
    scientific forecast models). Concrete implementations are intended to
    abstract the communication with their corresponding worker.

    .. code::

        class SaSSWorkerHandle(SeismicityWorkerHandle):
            MODEL_ID = 'SaSS'
            API_VERSION = 'v1'

    """
    API_VERSION = 'v1'
    PATH_RAMSIS_WORKER_SCENARIOS = '/runs'

    LOGGER = 'ramsis.core.remote_seismicity_worker_handle'

    class EncodingError(WorkerHandleBase.WorkerHandleError):
        """Error while encoding payload ({})."""

    class DecodingError(WorkerHandleBase.WorkerHandleError):
        """Error while decoding response ({})."""

    class WorkerError(WorkerHandleBase.WorkerHandleError):
        """Base worker error ({})."""

    class ConnectionError(WorkerError):
        """Worker connection error (url={!r}, reason={!r})."""

    class QueryResult(object):
        """
        Implementation of a query result. Partly implements the interface from
        :py:class:`sqlalchemy.orm.query.Query`.
        """

        def __init__(self, resp):
            """
            :param resp: *RT-RAMSIS* worker responses.
            :type resp: list or dict
            """

            if not isinstance(resp, list):
                resp = [resp]
            self._resp = resp

        # __init__ ()

        @classmethod
        def from_requests(cls, resp):
            """
            :param resp: *RT-RAMSIS* worker responses.
            :type resp: list or :py:class:`requests.Response`
            """
            def flatten(l):
                for el in l:
                    if (isinstance(el, collections.Iterable) and not
                            isinstance(el, (str, bytes, dict))):
                        yield from flatten(el)
                    else:
                        yield el

            # flatten ()

            def _json(resp):
                """
                Return a JSON encoded query result.
                """
                if not resp:
                    return []

                try:
                    resp_json = [r.json() for r in resp]
                except ValueError as err:
                    raise RemoteSeismicityWorkerHandle.DecodingError(err)

                return list(flatten(resp_json))

            # _json ()

            if not isinstance(resp, list):
                resp = [resp]

            return cls(_json(resp))

        # from_requests ()

        def filter_by(self, **kwargs):
            """
            Apply the given filtering criterion to a copy of the
            :py:class:`QueryResult`, using keyword expressions.

            Multiple criteria may be specified as comma separated; the effect
            is that they will be joined together using a logical :code:`and`.
            """
            # XXX(damb): Validate filter conditions
            try:
                filter_conditions = FilterSchema().load(kwargs)
            except marshmallow.exceptions.ValidationError as err:
                raise RemoteSeismicityWorkerHandle.WorkerHandleError(err)

            retval = []
            for resp in self._resp:
                if (resp is not None and
                    all(resp[k] == v
                        for k, v in filter_conditions.items())):
                    retval.append(resp)

            return self.__class__(retval)

        # filter_by ()

        def all(self):
            """
            Return the results represented by this :py:class:`QueryResult` as a
            list.
            """
            return self._resp

        # all ()

        def count(self):
            """
            Return a count this :py:class:`QueryResult` would return.
            """
            return len(self._resp)

        # count ()

        def first(self):
            """
            Return the first result of the :py:class:`QueryResult` or None if
            the result is empty.
            """
            if not self.count():
                return None

            return self._resp[0]

        # first ()

        def load(self, serializer):
            """
            Return a serialized query result.

            :param serializer: Serializer to be used for data serialization.
            :type serializer: :py:class:`marshmallow.Schema`
            """
            try:
                return serializer(many=True).load(self._resp.json())
            except (ValueError, marshmallow.exceptions.ValidationError) as err:
                raise RemoteSeismicityWorkerHandle.DecodingError(err)

        # load ()

    # class QueryResult

    class Payload(object):
        """
        Representation of the payload sent to the remote seismicity forecast
        worker. Encapsulates data model specific facilities.

        .. note::

            At the time being seismicity forecasts only hanlde a single
            injection well. As a consequence, the scenario forecasted is a
            single injection plan. Time depended injection well geometries
            currently are not supported (Those would be also part of the
            scenario).
        """

        DEFAULT_SERIALIZER = SFMWorkerInputMessageSchema

        def __init__(self, seismic_catalog, well, scenario, reservoir,
                     model_parameters, **kwargs):
            """
            :param str seismic_catalog: Snapshot of a seismic catalog in
            `QuakeML <https://quake.ethz.ch/quakeml/QuakeML>` format
            :param well: Snapshot of the injection well / borehole including
                the hydraulics.
            :type well: :py:class:`ramsis.datamodel.well.InjectionWell`
            :param scenario: The scenario to be forecasted
            :type scenario:
                :py:class:`ramsis.datamodel.hydraulics.InjectionPlan`
            :param str reservoir: Reservoir geometry in `WKT
                <https://en.wikipedia.org/wiki/Well-known_text_representation_of_geometry>`_
                format
            :param dict model_parameters: Model specific configuration
                parameters
            :param serializer: Serializer used to serialize the payload
            :type serializer: :py:class:`marshmallow.Schema`
            """
            well = self.validate_ctor_args(well)
            self._payload = {
                'seismic_catalog': {'quakeml': seismic_catalog},
                'well': well,
                'scenario': scenario,
                'reservoir': {'geom': reservoir},
                'model_parameters': model_parameters}

            self._serializer = kwargs.get(
                'serializer', self.DEFAULT_SERIALIZER)

        # __init__ ()

        def dumps(self):
            return self._serializer.dump(self._payload)

        @staticmethod
        def validate_ctor_args(well):
            if len(well.hydraulics) == 1:
                return well
            raise ValueError(
                "A well must have only a single hydraulics time series.")

        # validate_ctor_args ()

    # class Payload

    def __init__(self, base_url, **kwargs):
        """
        :param str base_url: The worker's base URL
        :param str model_id: Model indentifier
        :param timeout: Timeout parameters past to the `requests
            <http://docs.python-requests.org/en/master/>`_ library functions
        :type timeout: float or tuple
        """
        self.logger = logging.getLogger(self.LOGGER)

        base_url, model_id = self.validate_ctor_args(
            base_url, model_id=kwargs.get('model_id', self.MODEL_ID))

        self._url_base = base_url
        self._model_id = model_id

        self._url_path = ('/{version}/{model}'.format(
            version=self.API_VERSION,
            model=self._model_id) + self.PATH_RAMSIS_WORKER_SCENARIOS)

        self._timeout = kwargs.get('timeout')

    # __init__ ()

    @classmethod
    def create(cls, base_url, worker_id, **kwargs):
        """
        Factory class method creating worker handels for a corresponding model.

        :param str base_url: Worker base URL
        :param str worker_id: Worker/Model identifier
        :param kwargs: Keyword value parameters passed to the
            :py:class:`WorkerHandle` constructor

        :returns: Instance of a concrete implementation of
            :py:class:`WorkerHandle`
        :rtype: :py:class:`WorkerHandle`

        :raises WorkerHandleError: If an invalid model identifier was passed
        """
        if 'SaSS' == worker_id:
            return SaSSWorkerHandle(base_url, **kwargs)

        raise cls.WorkerHandleError(
            'Invalid worker identifier: {!r}'.format(worker_id))

    # create ()

    @property
    def model(self):
        return self._model_id

    @property
    def url(self):
        return self._url_base + self._url_path

    def query(self, task_ids=[]):
        """
        Query the result for worker's tasks.

        :param task_ids: List of task identifiers (:py:class:`uuid.UUID`). If
            an empty list is passed all results are requested.
        :type task_ids: list or :py:class:`uuid.UUID`
        :param serializer: Serializer to be used for data serialization. If
            :code:`None` no serialization is performed at all.
        :type serializer: :py:class:`marshmallow.Schema` or None
        """
        if not task_ids:
            self.logger.debug(
                'Requesting tasks results (model={!r}) (bulk mode).'.format(
                    self.model))
            try:
                resp = requests.get(self.url, timeout=self._timeout)
            except requests.exceptions.RequestException as err:
                raise self.ConnectionError(self.url, err)

            if resp.status_code in (StatusCode.TaskNotAvailable.value,
                                    StatusCode.WorkerError.value):
                self.logger.warning(
                    'WorkerError (code={}).'.format(resp.status_code))
                resp = []

            return self.QueryResult.from_requests(resp)

        # query results sequentially
        if isinstance(task_ids, uuid.UUID):
            task_ids = [task_ids]

        self.logger.debug(
            'Requesting tasks results (model={!r}, task_ids={!r}).'.format(
                self.model, task_ids))
        resp = []
        for t in task_ids:
            url = '{url}/{task_id}'.format(url=self.url, task_id=t)
            self.logger.debug(
                'Requesting result (model={!r}, url={!r}, task_id={!r}).'.
                format(self.model, url, t))
            try:
                response = requests.get(url, timeout=self._timeout)
            except requests.exceptions.RequestException as err:
                raise self.ConnectionError(url, err)

            self.logger.debug(
                'Task result (model={!r}, task_id={!r}): {!r}'.format(
                    self.model, t, response))

            if response.status_code not in (StatusCode.TaskNotAvailable.value,
                                            StatusCode.WorkerError.value):
                resp.append(response)
            else:
                self.logger.warning(
                    'WorkerError (code={}).'.format(response.status_code))

        return self.QueryResult.from_requests(resp)

    # query ()

    def compute(self, payload, **kwargs):
        """
        Issue a task to a remote seismicity forecast worker.

        :param payload: Payload sent to the remote worker
        :type payload: :py:class:`SeismicityWorkerHandle.Payload`
        :param serializer: Optional serializer used to load the response
        :type serializer: :py:class:`marshmallow.Schema`
        """
        # TODO(damb): Howto extract the correct hydraulics catalog for the
        # injection well?
        # -> Something like well.snapshot(hydraulics_idx=0) might be
        # implemented returning the current well with an hydraulics catalog
        # snapshot.

        serializer = kwargs.get('serializer_receive')

        # serialize payload
        try:
            _payload = payload.dumps()
        except marshmallow.exceptions.ValidationError as err:
            raise self.EncodingError(err)

        self.logger.debug(
            'Sending computation request (model={!r}, url={!r}).'.format(
                self.model, self.url))
        try:
            response = requests.post(self.url, data=_payload,
                                     timeout=self._timeout)
        except requests.exceptions.RequestException as err:
            raise self.ConnectionError(err)

        try:
            result = response.json()
            if serializer:
                result = serializer().load(result)
        except (ValueError, marshmallow.exceptions.ValidationError) as err:
            raise self.DecodingError(err)

        self.logger.debug(
            'Worker response (model={!r}, url={!r}): {!r}.'.format(
                self.model, self.url, result))
        return result

    # _compute ()

    _run = compute

    def delete(self, task_ids=[]):
        """
        Remove a worker's task.
        :param task_ids: List of task identifiers (:py:class:`uuid.UUID`)
        :type task_ids: list or :py:class:`uuid.UUID`
        """
        if not task_ids:
            raise NotImplementedError('Bulk removal not implemented, yet.')

        if isinstance(task_ids, uuid.UUID):
            task_ids = [task_ids]

        self.logger.debug(
            'Removing tasks (model={!r}, task_ids={!r}).'.format(
                self.model, task_ids))

        resp = []
        for t in task_ids:
            url = '{url}/{task_id}'.format(url=self.url, task_id=t)
            self.logger.debug(
                'Removing task (model={!r}, url={!r}, task_id={!r}).'.
                format(self.model, url, t))
            try:
                response = requests.delete(url, timeout=self._timeout)
            except requests.exceptions.RequestException as err:
                raise self.ConnectionError(url, err)

            self.logger.debug(
                'Task removed (model={!r}, task_id={!r}): {!r}'.format(
                    self.model, t, response))

            if response.status_code not in (StatusCode.TaskNotAvailable.value,
                                            StatusCode.WorkerError.value):
                resp.append(response)
            else:
                self.logger.warning(
                    'WorkerError (code={}).'.format(response.status_code))

        return self.QueryResult.from_requests(resp)

    # delete ()

    def __repr__(self):
        return '<%s (model=%r, url=%r)>' % (type(self).__name__,
                                            self.model, self.url)

    @staticmethod
    def validate_ctor_args(base_url, model_id):
        url = urlparse(base_url)
        if url.path or url.params or url.query or url.fragment:
            raise ValueError("Invalid URL.")

        if not model_id:
            raise ValueError("Missing: model id.")

        return url.geturl(), model_id

    # validate_ctor_args ()

# class SeismicityWorkerHandle


SeismicityWorkerHandle = RemoteSeismicityWorkerHandle
WorkerHandleBase.register(SeismicityWorkerHandle)


class SaSSWorkerHandle(SeismicityWorkerHandle):
    MODEL_ID = 'SaSS'
    API_VERSION = 'v1'


# ---- END OF <worker.py> ----

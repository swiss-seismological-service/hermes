# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Seismicity forecast model (SFM) worker related facilities.
"""

import enum
import uuid

from urllib.parse import urlparse

import marshmallow
import requests

from marshmallow import Schema, fields, validate

from RAMSIS.core.worker import WorkerHandleBase
from RAMSIS.io.sfm import SFMWorkerIMessageSerializer


KEY_DATA = 'data'
KEY_ATTRIBUTES = 'attributes'


class StatusCode(enum.Enum):
    """
    SFM-Worker status code enum.
    """
    # codes related to worker states
    TaskAccepted = 202
    TaskProcessing = 423
    TaskError = 418
    TaskCompleted = 200
    TaskNotAvailable = 204
    # codes related to worker resource
    HTTPMethodNotAllowed = 405
    UnprocessableEntity = 422
    WorkerError = 500


class FilterSchema(Schema):

    status = fields.Str(
        validate=validate.OneOf(
            choices=[c.name for c in StatusCode],
            error=('Invalid status given: (input={input}, '
                   'choices={choices}.')))
    status_code = fields.Int(
        validate=validate.OneOf(
            choices=[c.value for c in StatusCode],
            error=('Invalid status given: (input={input}, '
                   'choices={choices}.')))


# -----------------------------------------------------------------------------
class RemoteSeismicityWorkerHandle(WorkerHandleBase):
    """
    Base class simplifying the communication with *RT-RAMSIS* remote seismicity
    forecast model worker implementations (i.e. webservice implementations of
    scientific forecast models). Concrete implementations are intended to
    abstract the communication with their corresponding worker.

    .. code::

        class EM1WorkerHandle(SeismicityWorkerHandle):
            MODEL_ID = 'EM1'
            API_VERSION = 'v1'

    """
    API_VERSION = 'v1'
    PATH_RAMSIS_WORKER_SCENARIOS = '/runs'

    MIMETYPE = 'application/json'
    LOGGER = 'ramsis.core.worker.remote_seismicity_worker_handle'

    class EncodingError(WorkerHandleBase.WorkerHandleError):
        """Error while encoding payload ({})."""

    class DecodingError(WorkerHandleBase.WorkerHandleError):
        """Error while decoding response ({})."""

    class RemoteWorkerError(WorkerHandleBase.WorkerHandleError):
        """Base worker error ({})."""

    class ConnectionError(RemoteWorkerError):
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

        @classmethod
        def from_requests(cls, resp, deserializer=None):
            """
            :param resp: SFM worker responses.
            :type resp: list of :py:class:`requests.Response or
                :py:class:`requests.Response`
            :param deserializer: Deserializer used
            :type deserializer: :py:class:`RAMSIS.io.DeserializerBase` or None
            """
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

                return resp_json

            def demux_data(resp):
                """
                Demultiplex the the responses' primary data. :code:`errors` and
                :code:`meta` is ignored.
                """
                retval = []
                for r in resp:
                    if KEY_DATA in r:
                        if isinstance(r[KEY_DATA], list):
                            for d in r[KEY_DATA]:
                                retval.append({KEY_DATA: d})
                        else:
                            retval.append({KEY_DATA: r[KEY_DATA]})

                return retval

            if not isinstance(resp, list):
                resp = [resp]

            if deserializer is None:
                return cls(demux_data(_json(resp)))
            return cls(deserializer._loado(demux_data(_json(resp))))

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
                    all(resp[KEY_DATA][KEY_ATTRIBUTES][k] == v
                        for k, v in filter_conditions.items())):
                    retval.append(resp)

            return self.__class__(retval)

        def all(self):
            """
            Return the results represented by this :py:class:`QueryResult` as a
            list.
            """
            return self._resp

        def count(self):
            """
            Return a count this :py:class:`QueryResult` would return.
            """
            return len(self._resp)

        def first(self):
            """
            Return the first result of the :py:class:`QueryResult` or None if
            the result is empty.
            """
            if not self.count():
                return None

            return self._resp[0]

        @staticmethod
        def _extract(obj):
            return obj[KEY_DATA] if KEY_DATA in obj else []

        @staticmethod
        def _wrap(value):
            return {KEY_DATA: value}

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

        DEFAULT_SERIALIZER = SFMWorkerIMessageSerializer

        def __init__(self, seismic_catalog, well, scenario, reservoir,
                     model_parameters=None, **kwargs):
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
            :param model_parameters: Model specific configuration parameters.
               If :code:`None` parameters are not appended.
            :type model_parameters: dict or None
            :param serializer: Serializer used to serialize the payload
            :type serializer: :py:class:`marshmallow.Schema`
            """
            self._payload = {
                'data': {
                    'attributes': {
                        'seismic_catalog': {'quakeml': seismic_catalog},
                        'well': well,
                        'scenario': scenario,
                        'reservoir': {'geom': reservoir}}}}

            if model_parameters is not None:
                self._payload['data']['attributes']['model_parameters'] = \
                    model_parameters

            self._serializer = kwargs.get(
                'serializer', self.DEFAULT_SERIALIZER)

        def dumps(self):
            return self._serializer().dumps(self._payload)

    def __init__(self, base_url, **kwargs):
        """
        :param str base_url: The worker's base URL
        :param str model_id: Model indentifier
        :param timeout: Timeout parameters past to the `requests
            <http://docs.python-requests.org/en/master/>`_ library functions
        :type timeout: float or tuple
        """
        super().__init__(**kwargs)

        base_url, model_id = self.validate_ctor_args(
            base_url, model_id=kwargs.get('model_id', self.MODEL_ID))

        self._url_base = base_url
        self._model_id = model_id

        self._url_path = ('/{version}/{model}'.format(
            version=self.API_VERSION,
            model=self._model_id) + self.PATH_RAMSIS_WORKER_SCENARIOS)

        self._timeout = kwargs.get('timeout')

    @classmethod
    def from_run(cls, model_run):
        """
        Create a :py:class:`RemoteSeismicityWorkerHandle` from a model run.

        :param model_run:
        :type model_run:
            :py:class:`ramsis.datamodel.seismicity.SeismicityModelRun`
        """
        # XXX(damb): Where to get additional configuration options from?
        # model_run.config? model.config? From somewhere else?
        return cls(model_run.model.url, model_run.model.name)

    @property
    def model(self):
        return self._model_id

    @property
    def url(self):
        return self._url_base + self._url_path

    def query(self, task_ids=[], deserializer=None):
        """
        Query the result for worker's tasks.

        :param task_ids: List of task identifiers (:py:class:`uuid.UUID`). If
            an empty list is passed all results are requested.
        :type task_ids: list or :py:class:`uuid.UUID`
        :param deserializer: Deserializer to be used for data deserialization.
            If :code:`None` no deserialization is performed at all.
        :type deserializer: :py:class:`RAMSIS.io.DeserializerBase` or None
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

            return self.QueryResult.from_requests(
                resp, deserializer=deserializer)

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

        return self.QueryResult.from_requests(
            resp, deserializer=deserializer)

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

        serializer = kwargs.get('serializer')

        # serialize payload
        try:
            _payload = payload.dumps()
        except marshmallow.exceptions.ValidationError as err:
            raise self.EncodingError(err)

        self.logger.debug(
            'Sending computation request (model={!r}, url={!r}).'.format(
                self.model, self.url))
        try:
            headers = {'Content-Type': self.MIMETYPE,
                       'Accept': 'application/json'}
            response = requests.post(self.url, data=_payload,
                                     headers=headers,
                                     timeout=self._timeout)
        except requests.exceptions.RequestException as err:
            raise self.ConnectionError(self.url, err)

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


SeismicityWorkerHandle = RemoteSeismicityWorkerHandle
WorkerHandleBase.register(SeismicityWorkerHandle)

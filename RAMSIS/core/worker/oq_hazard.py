# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Openquake worker facilities
"""
from os.path import dirname, join
import enum
import functools
import uuid

from urllib.parse import urlparse

import marshmallow
import requests

from marshmallow import Schema, fields, validate

from RAMSIS.core.worker import WorkerHandleBase


DATETIME_FORMAT = '%Y-%m-%dT-%H-%M'
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
class OQHazardWorkerHandle(WorkerHandleBase):
    """
    Base class simplifying the communication with *RT-RAMSIS* oq hazard
    forecast model worker implementations (i.e. webservice implementations of
    scientific forecast models). Concrete implementations are intended to
    abstract the communication with their corresponding worker.

    .. code::

        class EM1WorkerHandle(OQHazardWorkerHandle):
            MODEL_ID = 'EM1'
            API_VERSION = 'v1'

    """
    API_VERSION = 'v1'
    PATH_CALC_RUN = '/calc/run'
    PATH_QUERY_STATUS = '/calc/{}/status'
    PATH_RESULTS_RUN = '/calc/{}/results'

    MIMETYPE = 'application/json'
    LOGGER = 'ramsis.core.worker.oq_hazard_worker_handle'

    class EncodingError(WorkerHandleBase.WorkerHandleError):
        """Error while encoding payload ({})."""

    class DecodingError(WorkerHandleBase.WorkerHandleError):
        """Error while decoding response ({})."""

    class RemoteWorkerError(WorkerHandleBase.WorkerHandleError):
        """Base worker error ({})."""

    class HTTPError(RemoteWorkerError):
        """Worker HTTP error (url={!r}, reason={!r})."""

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
        def from_requests(cls, resp, deserializer=None, resp_format='json',
                          **kwargs):
            """
            :param resp: SFM worker responses.
            :type resp: list of :py:class:`requests.Response or
                :py:class:`requests.Response`
            :param deserializer: Deserializer used. The deserializer must be
                configured to deserialize *many* values.
            :type deserializer: :py:class:`ramsis.io.DeserializerBase` or None
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
                    raise OQHazardWorkerHandle.DecodingError(err)

                return resp_json

            if not isinstance(resp, list):
                resp = [resp]
            ikwargs = {}
            if kwargs.get('output_type'):
                ikwargs['output_type'] = kwargs.get('output_type')

            if resp_format == 'json':
                if deserializer is None:
                    return cls(_json(resp))
                return cls(deserializer._loado(_json(resp, **ikwargs)))
            if resp_format == 'xml':
                print("format in xml", resp)
                resp_cls = cls(deserializer._loado(resp, **ikwargs))
                return resp_cls

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
                raise OQHazardWorkerHandle.WorkerHandleError(err)

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

    def __init__(self, base_url, model_run_id,
                 scenario_id, **kwargs):
        """
        :param str base_url: The worker's base URL
        :param str model_id: Model indentifier
        :param timeout: Timeout parameters past to the `requests
            <http://docs.python-requests.org/en/master/>`_ library functions
        :type timeout: float or tuple
        """
        super().__init__(**kwargs)

        self.base_url = self.validate_ctor_args(base_url)
        self.model_run_id = model_run_id
        self.scenario_id = scenario_id

        self._url_path = f"/{self.API_VERSION}"

        self._timeout = kwargs.get('timeout')

    @classmethod
    def from_run(cls, model_run):
        """
        Create a :py:class:`OQHazardWorkerHandle` from a model run.

        :param model_run:
        :type model_run:
            :py:class:`ramsis.datamodel.hazard.HazardModelRun`
        """
        # XXX(damb): Where to get additional configuration options from?
        # model_run.config? model.config? From somewhere else?
        return cls(model_run.model.url, model_run.id,
                   model_run.forecaststage.scenario.id)

    @property
    def url(self):
        return self.base_url + self._url_path

    @property
    def model(self):
        return self.model_id

    def query(self, task_id):
        """
        Query the result for worker's tasks.

        :param task_ids: List of task identifiers (:py:class:`uuid.UUID`). If
            an empty list is passed all results are requested.
        :type task_ids: list or :py:class:`uuid.UUID`
        """
        print("query")
        query_url = f'{self.PATH_QUERY_STATUS}'.format(task_id)
        url = f'{self.url}{query_url}'
        self.logger.debug(
            f'Requesting result OQ hazard(url={url}, task_id={task_id}).')

        req = functools.partial(
            requests.get, url, timeout=self._timeout)

        response = self._handle_exceptions(req)

        self.logger.debug(
            'Task result OQ hazard(task_id={task_id}): {response}')

        return self.QueryResult.from_requests(
            response)

    def query_results(self, task_id, deserializer=None):
        """
        Query the result for worker's tasks.

        :param task_ids: List of task identifiers (:py:class:`uuid.UUID`). If
            an empty list is passed all results are requested.
        :type task_ids: list or :py:class:`uuid.UUID`
        :param deserializer: Deserializer instance to be used for data
            deserialization.  If :code:`None` no deserialization is performed
            at all. The deserializer must be configured to deserialize *many*
            values.
        :type deserializer: :py:class:`ramsis.io.DeserializerBase` or None
        """
        query_url = f'{self.PATH_RESULTS_RUN}'.format(task_id)
        url = f'{self.url}{query_url}'
        self.logger.debug(
            f'Requesting result OQ hazard(url={url}, task_id={task_id}).')

        req = functools.partial(
            requests.get, url, timeout=self._timeout)

        response = self._handle_exceptions(req)

        self.logger.debug(
            'Task result OQ hazard(task_id={task_id}): {response}')

        return self.QueryResult.from_requests(
            response, deserializer=deserializer)

    def query_result_file(self, result_dict, deserializer=None):
        """
        Query the result for worker's tasks.

        :param task_ids: List of task identifiers (:py:class:`uuid.UUID`). If
            an empty list is passed all results are requested.
        :type task_ids: list or :py:class:`uuid.UUID`
        :param deserializer: Deserializer instance to be used for data
            deserialization.  If :code:`None` no deserialization is performed
            at all. The deserializer must be configured to deserialize *many*
            values.
        :type deserializer: :py:class:`ramsis.io.DeserializerBase` or None
        """
        url = result_dict['url']
        htype = result_dict['type']
        self.logger.debug(
            f'Requesting result file for OQ hazard (url={url}, type={htype}).')

        req = functools.partial(
            requests.get, url, params={'export_type': 'xml'},
            timeout=self._timeout)

        response = self._handle_exceptions(req)

        self.logger.debug(
            'Task result OQ hazard (url={url}): {response}')
        return self.QueryResult.from_requests(
            response, deserializer=deserializer,
            resp_format='xml', output_type=htype)

    def compute(self, job_config_filename, logic_tree_filename,
                gmpe_logic_tree_filename, model_source_filenames,
                oq_input_dir, **kwargs):
        """
        Issue a task to a hazard forecast worker.

        :param payload: Payload sent to the remote worker
        :type payload: :py:class:`HazardWorkerHandle.Payload`
        :param deserializer: Optional deserializer instance used to load the
            response
        """
        url_post = f'{self.url}{self.PATH_CALC_RUN}'
        self.logger.debug(
            'Sending computation request OQ hazard '
            f'(dir={dirname(job_config_filename)}, url={url_post})')
        oq_input_files = [
            (job_config_filename, (job_config_filename,
             open(join(oq_input_dir, job_config_filename), 'rb'), "text/ini")),
            (logic_tree_filename, (logic_tree_filename,
             open(join(oq_input_dir, logic_tree_filename), 'rb'), "text/xml")),
            (gmpe_logic_tree_filename, (gmpe_logic_tree_filename,
             open(join(oq_input_dir, gmpe_logic_tree_filename), 'rb'),
             "text/xml"))]

        model_index = 1
        for source_file in model_source_filenames:
            oq_input_files.append(
                (f'input_model_{model_index}',
                 (source_file, open(join(oq_input_dir, source_file), 'rb'),
                  "text/xml")))
            model_index += 1

        req = functools.partial(
            requests.post, url_post, files=oq_input_files)
        response = self._handle_exceptions(req)
        try:
            result = response.json()
        except ValueError as err:
            raise self.DecodingError(err)

        self.logger.debug(
            f'Worker response OQ hazard (dir={dirname(job_config_filename)},'
            f' url={url_post}, result: {result})')
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
            f'Removing tasks (model_run={self.model_run_id}, '
            f'task_ids={task_ids})')

        resp = []
        for t in task_ids:
            url = '{url}/{task_id}'.format(url=self.url, task_id=t)
            self.logger.debug(
                f'Removing task (model={self.model_run_id}, url={url}, '
                f'task_id={t})')
            req = functools.partial(requests.delete, url,
                                    timeout=self._timeout)
            response = self._handle_exceptions(req)

            self.logger.debug(
                f'Task removed (model={self.model_run_id}, task_id={t}): '
                f'{response}')

            resp.append(response)

        return self.QueryResult.from_requests(resp)

    def _handle_exceptions(self, req):
        """
        Provide generic exception handling when executing requests.

        :param callable req: :code:`requests` callable to be executed.
        """
        try:
            resp = req()
            resp.raise_for_status()
        except requests.exceptions.HTTPError as err:
            try:
                self.logger.warning(
                    f'JSON response (HTTPError): {resp.json()!r}')
            except Exception:
                pass
            finally:
                raise self.HTTPError(self.url, err)
        except requests.exceptions.ConnectionError as err:
            raise self.ConnectionError(self.url, err)
        except requests.exceptions.RequestException as err:
            raise self.RemoteWorkerError(err)

        return resp

    def __repr__(self):
        return '<%s (model=%r, url=%r)>' % (type(self).__name__,
                                            self.model_run_id, self.url)

    @staticmethod
    def validate_ctor_args(base_url):
        url = urlparse(base_url)
        if url.path or url.params or url.query or url.fragment:
            raise ValueError(f"Invalid URL: {url!r}.")

        return url.geturl()


WorkerHandleBase.register(OQHazardWorkerHandle)

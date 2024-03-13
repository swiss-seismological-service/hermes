"""
Seismicity forecast model (SFM) worker related facilities.
"""

import json
import enum
import functools
import uuid

from urllib.parse import urlparse

import marshmallow
from requests import get, post, delete, exceptions
from prefect import get_run_logger
from marshmallow import Schema, fields, validate

from RAMSIS.error import Error


KEY_DATA = 'data'
KEY_ATTRIBUTES = 'attributes'


class WorkerError(Error):
    """Base worker error ({})."""


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
class RemoteSeismicityWorkerHandle:
    """
    Base class simplifying the communication with *RT-RAMSIS* remote seismicity
    forecast model worker implementations (i.e. webservice implementations of
    scientific forecast models).
    """

    URI_BASE = '/v1/sfm/run'

    MIMETYPE = 'application/json'
    LOGGER = 'ramsis.remote_seismicity_worker_handle'

    class EncodingError(WorkerError):
        """Error while encoding payload ({})."""

    class DecodingError(WorkerError):
        """Error while decoding response ({})."""

    class RemoteWorkerError(WorkerError):
        """Base worker error ({})."""

    class DeserializationError(WorkerError):
        """Deserialization of model result error ({})."""

    class HTTPError(WorkerError):
        """Worker HTTP error (url={!r}, reason={!r})."""

    class ConnectionError(WorkerError):
        """Worker connection error (url={!r}, reason={!r})."""

    class QueryResult:
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

        @classmethod
        def from_requests(cls, resp, deserializer=None):
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
                    raise RemoteSeismicityWorkerHandle.DecodingError(err)

                return resp_json

            def demux_data(resp):
                """
                Demultiplex the responses' primary data. :code:`errors` and
                :code:`meta` are ignored.
                """
                retval = []
                for r in resp:
                    if KEY_DATA in r:
                        if isinstance(r[KEY_DATA], list):
                            for d in r[KEY_DATA]:
                                retval.append({KEY_DATA: d})
                        else:
                            retval.append({KEY_DATA: r[KEY_DATA]})

                # Uncomment if creating new test resources
                # from uuid import UUID

                # class UUIDEncoder(json.JSONEncoder):
                #     def default(self, obj):
                #         if isinstance(obj, UUID):
                #             # if the obj is uuid, we simply return the
                #             #value of uuid
                #             return obj.hex
                #         return json.JSONEncoder.default(self, obj)
                # if retval:
                #     with open(
                #         '../../tests/results/model_response_natural.json',
                #         'w') as f:
                #         f.write(json.dumps(retval, cls=UUIDEncoder))
                return retval

            if not isinstance(resp, list):
                resp = [resp]

            if deserializer is None:
                return cls(demux_data(_json(resp)))
            return cls(deserializer._loado(demux_data(_json(resp))))

    def __init__(self, base_url, **kwargs):
        """
        :param str base_url: The worker's base URL
        :param timeout: Timeout parameters past to the `requests
            <http://docs.python-requests.org/en/master/>`_ library functions
        :type timeout: float or tlple
        """
        self.logger = get_run_logger()
        base_url = self.validate_ctor_args(
            base_url)

        self._url_base = base_url

        self._url_path = f"{self.URI_BASE}"

        self._timeout = kwargs.get('timeout')

    @property
    def url(self):
        return self._url_base + self._url_path

    def query(self, task_ids=[], deserializer=None):
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
        if not task_ids:
            self.logger.debug(
                'Requesting tasks results (bulk mode).')
            self.logger.info(f"URL for model: {self.url}")
            req = functools.partial(
                get, self.url, timeout=self._timeout)

            resp = self._handle_exceptions(req)

            return self.QueryResult.from_requests(
                resp, deserializer=deserializer)

        # query results sequentially
        if isinstance(task_ids, uuid.UUID):
            task_ids = [task_ids]

        self.logger.debug(
            'Requesting tasks results task_ids={!r}).'.format(
                task_ids))
        resp = []
        for t in task_ids:
            url = '{url}/{task_id}'.format(url=self.url, task_id=t)
            self.logger.info(
                'Requesting result (url={!r}, task_id={!r}).'.
                format(url, t))

            req = functools.partial(
                get, url, timeout=(5, 30))

            response = self._handle_exceptions(req)

            self.logger.debug(
                'Task result (task_id={!r}): {!r}'.format(
                    t, response))
            resp.append(response)
        try:
            return self.QueryResult.from_requests(
                resp, deserializer=deserializer)
        except Exception as err:
            raise self.DeserializationError(err)

    def compute(self, payload, serializer, deserializer, **kwargs):

        try:
            _payload = json.dumps(serializer._serialize_dict(payload))
        except Exception as err:
            raise self.EncodingError(err)
        self.logger.info(
            'Sending computation request url={!r}).'.format(
                self.url))

        headers = {'Content-Type': self.MIMETYPE,
                   'Accept': 'application/json'}
        req = functools.partial(
            post, self.url, data=_payload, headers=headers,
            timeout=self._timeout)
        response = self._handle_exceptions(req)

        try:
            result_json = response.json()
            result = deserializer._loado(result_json)

            # Uncomment if creating new test resources
            # from uuid import UUID

            # class UUIDEncoder(json.JSONEncoder):
            #     def default(self, obj):
            #         if isinstance(obj, UUID):
            #             # if the obj is uuid, we simply return the value
            #             # of uuid
            #             return obj.hex
            #         return json.JSONEncoder.default(self, obj)
            # with open(
            #     '../../tests/results/model_response_to_post_natural.json',
            #     'w') as f:
            #     f.write(json.dumps(result, cls=UUIDEncoder))

        except (ValueError, marshmallow.exceptions.ValidationError) as err:
            raise self.DecodingError(err)
        except Exception as err:
            self.logger.error(err)
            raise

        self.logger.debug(
            'Worker response (url={!r}): {!r}.'.format(
                self.url, result))
        return result

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
            'Removing tasks (task_ids={!r}).'.format(
                task_ids))

        resp = []
        for t in task_ids:
            url = '{url}/{task_id}'.format(url=self.url, task_id=t)
            self.logger.debug(
                'Removing task (url={!r}, task_id={!r}).'.
                format(url, t))

            req = functools.partial(delete, url,
                                    timeout=self._timeout)
            response = self._handle_exceptions(req)

            self.logger.info(
                'Task removed (task_id={!r}): {!r}'.format(
                    t, response))

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
        except exceptions.HTTPError as err:
            try:
                self.logger.warning(
                    f'JSON response (HTTPError): {resp.json()!r}')
            except Exception:
                pass
            finally:
                raise self.HTTPError(self.url, err)
        except exceptions.ConnectionError as err:
            self.logger.error("The request has a connection error to"
                              f" {self._url_base}. Please check if the "
                              "connection is accepting requests")
            raise self.ConnectionError(self.url, err)
        except exceptions.RequestsError as err:
            self.logger.error(f"The request has an error {self.url}")
            raise self.RemoteWorkerError(err)
        except exceptions.Timeout:
            self.logger.error(f"The request timed out to {self.url}")
            raise

        return resp

    def __repr__(self):
        return '<%s (url=%r)>' % (type(self).__name__,
                                  self.url)

    @staticmethod
    def validate_ctor_args(base_url):
        url = urlparse(base_url)
        if url.path or url.params or url.query or url.fragment:
            raise ValueError(f"Invalid URL: {url}.")

        return url.geturl()

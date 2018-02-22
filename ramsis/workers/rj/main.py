import logging
from flask import Flask, got_request_exception
from flask_restful import Api

from .resources import Run


def log_exception(sender, exception, **extra):
    sender.logger.debug('Got exception during processing: %s', exception)


def main():
    app = Flask('rj_worker')
    app.debug = True
    api = Api(app)
    api.add_resource(Run, '/run')

    app.logger.setLevel(logging.DEBUG)
    got_request_exception.connect(log_exception, app)
    app.logger.info('Starting RJ Worker')

    app.run(host='0.0.0.0', port=5000, use_reloader=False)


if __name__ == '__main__':
    main()

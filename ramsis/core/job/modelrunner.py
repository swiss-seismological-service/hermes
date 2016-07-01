import logging

from PyQt4 import QtCore


class ModelRunner(QtCore.QObject):
    """
    The `ModelRunner` manages the actual IS models which live on a separate
    thread each. It communicates data back and forth in a thread safe manner
    and replicates some of the model's basic properties (name etc.) to make
    them available on the main thread.

    :param `Model` model: ISHA model that the controller should manage

    """

    # This is for debugging since breakpoints don't work with threads
    DEBUG = False

    def __init__(self, model):
        super(ModelRunner, self).__init__()
        # the reference to the actual model is private since it must not be
        # accessed from the main thread directly.
        self._logger = logging.getLogger(__name__)
        self.model = model
        if not ModelRunner.DEBUG:
            self._qthread = QtCore.QThread()
            self._qthread.setObjectName(model.title)
            self.model.moveToThread(self._qthread)
            self._qthread.started.connect(self.model.run)
        else:
            self._logger.warning('DEBUG mode, {} will run in main thread'
                                 .format(model.title))

        self.model.finished.connect(self._on_model_finished)
        self._logger = logging.getLogger(__name__)

    def __del__(self):
        # Make sure the thread ends before we destroy it
        if not ModelRunner.DEBUG:
            self._qthread.wait()

    def run_model(self, run_data):
        """
        Starts a model run with the information given in run_data

        :param ModelInput run_data: model inputs and parameters for this
            forecast

        """
        self._logger.debug('preparing %s', self.model.title)
        self.model.prepare_run(run_data)
        self._logger.debug('starting worker thread for {}'
                           .format(self.model.title))
        if not ModelRunner.DEBUG:
            self._qthread.start()
        else:
            self.model.run()

    def _on_model_finished(self):
        """ Finished handler. The model is done so we can quit the thread """
        if ModelRunner.DEBUG:
            return
        self._qthread.quit()
        self._qthread.wait()

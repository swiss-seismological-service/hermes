# Copyright 2018, ETH Zurich - Swiss Seismological Service SED
"""
Dialog related GUI facilities.
"""

import collections
import json
import logging

from PyQt5.QtCore import pyqtSlot, Qt
from PyQt5.QtWidgets import QDialog, QWidget, QFileDialog, QMessageBox

from ramsis.utils.error import Error
from ramsis.datamodel.forecast import EStage
from ramsis.datamodel.well import InjectionWell

from RAMSIS.io.hydraulics import (
    HYDWSBoreholeHydraulicsDeserializer, HYDWSJSONIOError)
from RAMSIS.io.utils import pymap3d_transform_geodetic2ned
from RAMSIS.ui.utils import UiForm
from RAMSIS.wkt_utils import is_phsf, wkb_to_wkt


class DialogError(Error):
    """Base Dialog Error ({})."""


class ValidationError(DialogError):
    """ValidationError: {!r}"""


class DialogBase(QDialog):
    """
    Base class for UI dialogs.
    """
    LOGGER = 'ramsis.ui.dialog'

    def __init__(self, *args, **kwargs):
        """
        Dialog initializer
        """
        super().__init__(*args, **kwargs)
        self._data = None

        self.logger = logging.getLogger(self.LOGGER)

    @property
    def data(self):
        return self._data

    def reject(self):
        self._data = None
        super().reject()

    def accept(self):
        try:
            self._on_accept()
        except DialogError as err:
            self.logger.error(f'{err}')
            self.reject()
        else:
            super().accept()

    def _on_accept():
        raise NotImplementedError


class ScenarioConfigDialog(
        DialogBase, UiForm('scenarioconfigdialog.ui')):
    """
    UI dialog for scenario configuration.
    """
    JSON_INDENT = 2

    def __init__(self, scenario, *args, fc_duration=None,
                 srs=None, **kwargs):
        """
        :param scenario: Forecast scenario the dialog is preconfigured with
        :type scenario: :py:class:`ramsis.datamodel.forecast.ForecastScenario`
        :param float fc_duration: Forecast duration in seconds
        :param str srs: Spatial reference system identifier (proj4) used for
            data import
        """
        super().__init__(*args, **kwargs)

        self._path_plan = None
        self._srs = srs
        self._data = scenario
        self._configure(scenario, fc_duration)

    def _configure(self, scenario, fc_duration=None):
        """
        Preconfigure the dialog with a forecast scenario.

        :param scenario: Forecast scenario the dialog is preconfigured with
        :type scenario: :py:class:`ramsis.datamodel.forecast.ForecastScenario`
        :param float fc_duration: Forecast duration in seconds
        """
        self.ui.scenarioEnable.setChecked(scenario.enabled)
        self.ui.nameLineEdit.setText(scenario.name)

        try:
            geom = wkb_to_wkt(scenario.reservoirgeom)
        except Exception:
            geom = str(scenario.reservoirgeom)

        self.ui.reservoirGeometryPlainTextEdit.setPlainText(geom)

        # configure seismicityStageTab
        try:
            stage = scenario[EStage.SEISMICITY]
        except KeyError:
            # TODO(damb): Disable tab? Enable/disable tabs does not make sense
            # since currently there is no possibility to add/remove stages. For
            # the time being stages are exclusively *edited*.
            pass
        else:
            self.ui.seismicityStageEnable.setChecked(stage.enabled)

            if fc_duration is not None:
                self.ui.predictionBinDurationDoubleSpinBox.setMaximum(
                    fc_duration)

            if stage.config and 'prediction_bin_duration' in stage.config:
                self.ui.predictionBinDurationDoubleSpinBox.setValue(
                    stage.config['prediction_bin_duration'])

            # configure seismicity models
            for r in stage.runs:
                self.ui.seismicityModelsComboBox.addItem(
                    r.model.name, userData=r)

            if stage.runs:
                self.ui.seismicityModelsComboBox.setCurrentIndex(0)

                if stage.runs[0].enabled is None:
                    self.ui.modelEnableCheckBox.setChecked(
                        stage.runs[0].model.enabled)
                else:
                    self.ui.modelEnableCheckBox.setChecked(
                        stage.runs[0].enabled)

                if stage.runs[0].config:
                    self.ui.modelPlainTextEdit.setPlainText(
                        json.dumps(stage.runs[0].config,
                                   indent=self.JSON_INDENT))
                else:
                    self.ui.modelPlainTextEdit.setPlainText(
                        json.dumps(stage.runs[0].model.config,
                                   indent=self.JSON_INDENT))

        # configure hazardStageTab
        try:
            stage = scenario[EStage.HAZARD]
        except KeyError:
            # TODO(damb): see seismicityStageTab
            pass
        else:
            self.ui.hazardStageEnable.setChecked(stage.enabled)

        # configure riskStageTab
        try:
            stage = scenario[EStage.RISK]
        except KeyError:
            # TODO(damb): see seismicityStageTab
            pass
        else:
            self.ui.riskStageEnable.setChecked(stage.enabled)

    def _on_accept(self):
        # validate stages
        seismicity_stage_enabled = self.ui.seismicityStageEnable.isChecked()
        hazard_stage_enabled = self.ui.hazardStageEnable.isChecked()
        risk_stage_enabled = self.ui.riskStageEnable.isChecked()
        if (hazard_stage_enabled and not seismicity_stage_enabled or
            risk_stage_enabled and not (seismicity_stage_enabled and
                                        hazard_stage_enabled)):
            _ = QMessageBox.critical(
                self, 'RAMSIS',
                'Invalid forecast stage configuration.',
                buttons=QMessageBox.Close)
            raise ValidationError(
                'Invalid forecast stage configuration.')

        wkt_geom = self.ui.reservoirGeometryPlainTextEdit.toPlainText()
        if not is_phsf(wkt_geom):
            _ = QMessageBox.critical(
                self, 'RAMSIS', f'Invalid reservoir geometry {wkt_geom!r}.',
                buttons=QMessageBox.Close)
            raise ValidationError(
                f'Invalid reservoir geometry passed {wkt_geom!r}')

        well = self._data.well
        # create injection plan
        if (self.ui.injectionStrategyRadioButton1.isChecked() and
                self._path_plan):

            deserializer_args = {'plan': True}
            # TODO TODO TODO
            if self._srs:
                deserializer_args.update({
                    'proj': self._srs,
                    'transform_callback': pymap3d_transform_geodetic2ned})

            deserializer = HYDWSBoreholeHydraulicsDeserializer(
                **deserializer_args)

            self.logger.debug(
                f'Importing injection plan {self._path_plan!r}')

            try:
                with open(self._path_plan, 'rb') as ifd:
                    well = deserializer.load(ifd)
            except (OSError, json.JSONDecodeError, HYDWSJSONIOError) as err:
                _ = QMessageBox.critical(
                    self, 'RAMSIS',
                    (f'Error while importing data from {self._path_plan!r}:'
                     f'\n{err}.'),
                    buttons=QMessageBox.Close)
                raise DialogError(
                    f'Importing data from {self._path_plan!r} failed ({err}).')
            else:
                self.logger.info(
                    'Injection plan sucessfully imported.')

                # TODO(damb): validate injection plan
        elif isinstance(self._data.well, InjectionWell):
            pass
        else:
            _ = QMessageBox.critical(
                self, 'RAMSIS',
                f'Invalid injection strategy configuration.',
                buttons=QMessageBox.Close)

            raise ValidationError(
                f'Invalid injection strategy configuration.')

        # complete scenario
        self._data.config = {}
        self._data.name = self.ui.nameLineEdit.text()
        self._data.reservoirgeom = wkt_geom
        self._data.well = well

        try:
            stage = self._data[EStage.SEISMICITY]
        except KeyError:
            pass
        else:
            stage.enabled = seismicity_stage_enabled
            stage.config = {
                'prediction_bin_duration':
                self.ui.predictionBinDurationDoubleSpinBox.value(), }
            cbox = self.ui.seismicityModelsComboBox
            stage.runs = [cbox.itemData(i) for i in range(cbox.count())]

        try:
            stage = self._data[EStage.HAZARD]
        except KeyError:
            pass
        else:
            stage.enabled = hazard_stage_enabled

        try:
            stage = self._data[EStage.RISK]
        except KeyError:
            pass
        else:
            stage.enabled = risk_stage_enabled

    @pyqtSlot(name='on_injectionStrategyImportFromFilePushButton_clicked')
    def import_plan_from_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        self._path_plan, _ = QFileDialog.getOpenFileName(
            QWidget(), "QFileDialog.getOpenFileName()",
            "", "All Files (*);;Borehole/Hydraulics Scenario (*.json)",
            options=options)

    @pyqtSlot(bool, name='on_injectionStrategyRadioButton1_toggled')
    def on_injection_strategy_rbtn_state_changed(self):
        self.ui.injectionStrategyImportFromFilePushButton.setEnabled(False)

        if self.ui.injectionStrategyRadioButton1.isChecked():
            self.ui.injectionStrategyImportFromFilePushButton.setEnabled(True)

    @pyqtSlot(int, name='on_seismicityModelsComboBox_currentIndexChanged')
    def update_sfm_config_view(self, idx):
        """
        Update the SFM model (run) specific configuration view.
        """
        m = self.ui.seismicityModelsComboBox.itemData(idx)

        self.ui.modelEnableCheckBox.setChecked(m.enabled)
        if m.config:
            self.ui.modelPlainTextEdit.setPlainText(
                json.dumps(m.config, indent=self.JSON_INDENT))
        else:
            self.ui.modelPlainTextEdit.setPlainText(
                json.dumps(m.model.config, indent=self.JSON_INDENT))

    @pyqtSlot(int, name='on_modelEnableCheckBox_stateChanged')
    def update_sfm_config_enabled(self, state):
        cbox = self.ui.seismicityModelsComboBox
        idx = cbox.currentIndex()
        m = cbox.itemData(idx)

        m.enabled = bool(state == Qt.Checked)
        cbox.setItemData(idx, m)

    @pyqtSlot(name='on_modelPlainTextEdit_textChanged')
    def update_sfm_config(self):
        cbox = self.ui.seismicityModelsComboBox
        idx = cbox.currentIndex()
        m = cbox.itemData(idx)

        try:
            m.config = json.loads(self.ui.modelPlainTextEdit.toPlainText())
        except json.JSONDecodeError:
            pass
        else:
            cbox.setItemData(idx, m)


class ForecastConfigDialog(
        DialogBase, UiForm('forecastconfigdialog.ui')):
    """
    UI dialog for forecast configuration.
    """
    DEFAULT_FORECAST_PROTOTYPE_INTERVAL = 21600
    DEFAULT_FORECAST_PROTOTYPE_TOTAL_INTERVALS = 1

    def __init__(self, forecast, *args, min_datetime=None, **kwargs):
        """
        :param min_datetime: minimum datetime for edit fields
        :type min_datetime: :py:class:`datetime.datetime`
        """
        super().__init__(*args, **kwargs)

        if min_datetime:
            self.ui.starttimeDateTimeEdit.setMinimumDateTime(min_datetime)
            self.ui.endtimeDateTimeEdit.setMinimumDateTime(min_datetime)

        self._data = forecast
        self._configure(forecast)

    def _configure(self, forecast):
        """
        Preconfigure the dialog with a forecast.

        :param forecast: Forecast to preconfigure the dialog from
        :type forecast: :py:class:`ramsis.datamodel.forecast.Forecast`
        """
        if forecast.name is not None:
            self.ui.nameLineEdit.setText(forecast.name)

        self.ui.starttimeDateTimeEdit.setDateTime(forecast.starttime)
        self.ui.endtimeDateTimeEdit.setDateTime(forecast.endtime)

        self.ui.enableForecastCheckBox.setChecked(forecast.enabled)

    def _on_accept(self):
        start = self.ui.starttimeDateTimeEdit.dateTime()
        end = self.ui.endtimeDateTimeEdit.dateTime()

        # validate
        if end <= start:
            _ = QMessageBox.critical(
                self, 'RAMSIS',
                'Endtime must be greater than starttime.',
                buttons=QMessageBox.Close)

            raise ValidationError(
                'Endtime must be greater than starttime.')

        self._data.name = self.ui.nameLineEdit.text()
        self._data.starttime = start.toPyDateTime()
        self._data.endtime = end.toPyDateTime()
        self._data.enabled = self.ui.enableForecastCheckBox.isChecked()


class CreateForecastSequenceDialog(
        DialogBase, UiForm('createforecastsequencedialog.ui')):
    """
    UI dialog for duplicating a forecast.
    """
    MAX_NUM_COPIES = 1000
    MAX_INTERVAL = 60 * 60 * 24 * 365  # one year

    RetVal = collections.namedtuple(
        'RetVal', ['endtime_fixed', 'interval', 'num_intervals'])

    def __init__(self, forecast, *args, **kwargs):
        """
        :param forecast: Forecast prototype to be cloned
        :type forecast: :py:class:`ramsis.datamodel.forecast.Forecast`
        """
        super().__init__(*args, **kwargs)
        self._forecast = forecast
        self._project = forecast.project

        self._fc_duration = forecast.duration
        self._fc_sequence_epoch_project = None
        if self._project.endtime:
            self._fc_sequence_epoch_project = (
                self._project.endtime - self._forecast.starttime -
                self._fc_duration)
        self._fc_sequence_epoch_fc = self._fc_duration

        self._configure()

    @pyqtSlot(float, name='on_intervalDoubleSpinBox_valueChanged')
    def update_num_copies(self, interval):
        if self.ui.fixedEndtimeCheckBox.isChecked():
            self.ui.numberCopiesDoubleSpinBox.setMaximum(
                int(self._fc_duration.total_seconds() / interval))
        else:
            if self._fc_sequence_epoch_project:
                max_num_copies = ((
                    self._fc_sequence_epoch_project.total_seconds() -
                    self._fc_duration.total_seconds()) / interval)

                self.ui.numberCopiesDoubleSpinBox.setMaximum(max_num_copies)

    @pyqtSlot(float, name='on_numberCopiesDoubleSpinBox_valueChanged')
    def update_interval(self, num_copies):
        if self.ui.fixedEndtimeCheckBox.isChecked():
            self.ui.intervalDoubleSpinBox.setMaximum(
                int(self._fc_duration.total_seconds() /
                    (num_copies + 1)))
        else:
            if self._fc_sequence_epoch_project:
                self.ui.intervalDoubleSpinBox.setMaximum(
                    int(self._fc_sequence_epoch_project.total_seconds() /
                        (num_copies + 1)))

    @pyqtSlot(int, name='on_fixedEndtimeCheckBox_stateChanged')
    def update_maximum(self, state):
        self._configure()

    def _configure(self):
        # configure defaults
        if self.ui.fixedEndtimeCheckBox.isChecked():
            num_intervals = 2
            interval = self._fc_duration.total_seconds() / num_intervals
            self.ui.numberCopiesDoubleSpinBox.setMaximum(
                (self._fc_duration.total_seconds() - interval) /
                num_intervals)
            self.ui.intervalDoubleSpinBox.setMaximum(interval)
        else:
            if self._fc_sequence_epoch_project:
                interval = 21600.
                max_num_copies = ((
                    self._fc_sequence_epoch_project.total_seconds() -
                    self._fc_duration.total_seconds()) / interval)

                self.ui.numberCopiesDoubleSpinBox.setMaximum(max_num_copies)
                self.ui.intervalDoubleSpinBox.setMaximum(interval)
            else:
                self.ui.numberCopiesDoubleSpinBox.setMaximum(
                    self.MAX_NUM_COPIES)
                self.ui.intervalDoubleSpinBox.setMaximum(self.MAX_INTERVAL)

    def _on_accept(self):
        self._data = self.RetVal(
            endtime_fixed=self.ui.fixedEndtimeCheckBox.isChecked(),
            interval=self.ui.intervalDoubleSpinBox.value(),
            num_intervals=int(self.ui.numberCopiesDoubleSpinBox.value()))

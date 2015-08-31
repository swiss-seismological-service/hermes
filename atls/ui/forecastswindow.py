# -*- encoding: utf-8 -*-
"""
Controller class for the forecasts window

Copyright (C) 2014, ETH Zurich - Swiss Seismological Service SED

"""

import os
import logging

from PyQt4 import QtGui, uic
from PyQt4.QtCore import Qt, QThread
import numpy as np
from qgis.core import QgsVectorLayer, QgsMapLayerRegistry, QgsRectangle
from qgis.gui import QgsMapCanvasLayer

from openquake.engine.db import models as oq_models

from core import ismodelcontrol as mc

from viewmodels.eventhistorymodel import EventListModel
from qgislayers import AtlsLossPoeLayer

ui_path = os.path.dirname(__file__)
FC_WINDOW_PATH = os.path.join(ui_path, 'views', 'forecastswindow.ui')
Ui_ForecastsWindow = uic.loadUiType(FC_WINDOW_PATH)[0]

# Map service that provides the background map
MAP_SOURCE_URL = 'http://server.arcgisonline.com/ArcGIS/rest/services/'\
                 'World_Street_Map/MapServer?f=json&pretty=true'


# Shape files for background map
BG_LAYER_PATH = 'resources/background_layers'
BG_LAYER_FILES = ['ne_10m_ocean.shp',
                  'ne_10m_admin_0_boundary_lines_land.shp',
                  'ne_10m_lakes.shp',
                  'ne_10m_land.shp']

# Shape colors
LAYER_COLORS = [QtGui.QColor.fromRgb(37, 52, 148),    # ocean
                QtGui.QColor.fromRgb(30, 30, 30),     # borders
                QtGui.QColor.fromRgb(65, 182, 196),   # lakes
                QtGui.QColor.fromRgb(250, 250, 250)]  # land


class TabPresenter(object):
    """
    Handles a tabs content

    This is an abstract class

    """
    def __init__(self, ui):
        """
        :param ui: reference to the Qt UI
        :type ui: Ui_ForecastsWindow

        """
        self.ui = ui
        self.presented_forecast = None
        self.logger = logging.getLogger(__name__)

    def present_forecast_result(self, result):
        """
        Set the forecast result that is to be displayed

        We also listen to changes to the currently displayed result to update
        the tabs content accordingly

        :param result: forecast result
        :type result: ForecastResult or None

        """
        if self.presented_forecast is not None:
            self.presented_forecast.result_changed.disconnect(self._on_change)
        self.presented_forecast = result
        if self.presented_forecast is not None:
            self.presented_forecast.result_changed.connect(self._on_change)
        self.refresh()

    def refresh(self):
        raise NotImplementedError("Please Implement this method")

    def _on_change(self):
        self.refresh()


class IsTabPresenter(TabPresenter):
    """
    Handles the Induced Seismicity tabs content

    """
    def __init__(self, ui):
        """
        :param ui: reference to the Qt UI
        :type ui: Ui_ForecastsWindow

        """
        super(IsTabPresenter, self).__init__(ui)

        # Populate the models chooser combo box
        self.ui.modelSelectorComboBox.currentIndexChanged.connect(
            self.action_model_selection_changed)
        for model in mc.active_models:
            self.ui.modelSelectorComboBox.addItem(model.title)

    def refresh(self):
        """
        Refresh everything

        """
        model_result = self._get_selected_model_result(self.presented_forecast)
        self._present_model_result(model_result)

    def _present_model_result(self, model_result):
        """
        Update the forecast results shown in the window with the ISModelResult
        passed in to the function.

        :param model_result: ISModelResult object to display or None to clear
        :type model_result: ISModelResult or None

        """

        self._show_spatial_is(model_result)
        self._show_is_rate(model_result)
        self._show_is_score(model_result)

    def _show_is_rate(self, model_result):
        """
        Update the forecast result labels

        :param model_result: latest model result
        :type model_result: ISModelResult or None

        """
        if model_result is None:
            self.ui.fcTimeLabel.setText('-')
            self.ui.predRateLabel.setText('-')
            self.ui.scoreLabel.setText('-')
        else:
            self.ui.fcTimeLabel.setText(model_result.t_run.ctime())
            rate = '{:.1f}'.format(model_result.cum_result.rate) \
                if not model_result.failed else 'No Results'
            self.ui.predRateLabel.setText(rate)

    def _show_is_score(self, model_result):
        """
        Update the model score labels (time and LL of latest rating)

        :param model_result: model result containing the latest score or None
        :type model_result: ISModelResult or None

        """
        if model_result is None or model_result.cum_result.score is None:
            ll = 'N/A'
            t = ''
        else:
            ll = '{:.1f}'.format(model_result.cum_result.score.LL)
            t = '@ {}'.format(model_result.t_run.ctime())
        self.ui.scoreLabel.setText(ll)
        self.ui.scoreTimeLabel.setText(t)

    def _show_spatial_is(self, model_result):
        """
        Show the latest spatial results (if available) for the model output
        passed into the method.

        :param model_result: model result or None
        :type model_result: ISModelResult or None

        """
        mr = model_result
        if mr is None or mr.failed or not mr.vol_results:
            self.ui.voxelPlot.set_voxel_data(None)
            self.logger.debug('No spatial results available to plot')
        else:
            vol_rates = [r.rate for r in mr.vol_results]
            self.logger.debug('Max voxel rate is {:.1f}'.
                              format(np.amax(vol_rates)))
            self.ui.voxelPlot.set_voxel_data(vol_rates)

    # Helpers

    def _get_selected_model_result(self, fc_result):
        if fc_result is None:
            return None
        is_result = fc_result.is_forecast_result
        if is_result is None:
            return None

        model_idx = self.ui.modelSelectorComboBox.currentIndex()
        model_name = mc.active_models[model_idx].title
        model_result = is_result.model_results.get(model_name)

        return model_result

    # Button Actions

    def action_model_selection_changed(self, _):
        model_result = self._get_selected_model_result(self.presented_forecast)
        self._present_model_result(model_result)


class HazardTabPresenter(TabPresenter):
    """
    Handles the Hazard tabs content

    """

    def refresh(self):
        self.logger.info('refreshing hazard on thread {}'
                         .format(QThread.currentThread().objectName()))
        calc_id = None
        if self.presented_forecast:
            calc_id = self.presented_forecast.hazard_oq_calc_id
        if calc_id is not None:
            self.ui.hazCalcIdLabel.setText(str(calc_id))
        else:
            self.ui.hazCalcIdLabel.setText('N/A')

        outputs = oq_models.Output.objects.filter(oq_job=calc_id)

        hazard_curves = (o.hazard_curve for o in outputs
                         if o.output_type == 'hazard_curve')

        imls = None
        for hc in hazard_curves:
            if hc.imt != 'MMI':
                # we only support mmi for now
                # TODO: show selection box for all IMTs
                continue

            # extract IMLs once
            if imls is None:
                imls = hc.imls

            # extract x, y, poes
            x_y_poes = oq_models.HazardCurveData.objects.all_curves_simple(
                filter_args=dict(hazard_curve=hc.id))

            x, y, poes = next(x_y_poes)  # there should be only one

            if hc.statistics == 'mean':
                pen = QtGui.QPen(Qt.red)
            elif hc.statistics == 'quantile':
                pen = QtGui.QPen(Qt.green)
            else:
                pen = QtGui.QPen(Qt.white)

            self.ui.hazPlot.plot(imls, poes, pen=pen)


class RiskTabPresenter(TabPresenter):
    """
    Handles the Hazard tabs content

    """

    def __init__(self, ui):
        super(RiskTabPresenter, self).__init__(ui)

        # Load layers

        shape_files = [os.path.join(BG_LAYER_PATH, shp_file)
                       for shp_file in BG_LAYER_FILES]
        layers = []
        for shp_file, color in zip(shape_files, LAYER_COLORS):
            self.logger.info('Loading {}'.format(shp_file))
            path = os.path.abspath(os.path.join(shp_file))
            layer = QgsVectorLayer(path, 'shp_file', 'ogr')
            if not layer.isValid():
                self.logger.info('Layer at {} failed to load!'.format(path))
            else:
                symbols = layer.rendererV2().symbols()
                symbol = symbols[0]
                symbol.setColor(color)
                layers.append(layer)
                QgsMapLayerRegistry.instance().addMapLayer(layer)

        self.loss_layer = AtlsLossPoeLayer('Loss')
        layers.append(self.loss_layer)

        # Set layers

        canvas_layers = [QgsMapCanvasLayer(l) for l in layers]
        self.ui.mapWidget.setExtent(QgsRectangle(5.6, 45.6, 10.8, 47.5))
        self.ui.mapWidget.setLayerSet(canvas_layers)

    def refresh(self):
        self.logger.info('refreshing risk')
        if self.presented_forecast:
            calc_id = self.presented_forecast.risk_oq_calc_id
        else:
            calc_id = None
        if calc_id is not None:
            self.ui.riskCalcIdLabel.setText(str(calc_id))
        else:
            self.ui.riskCalcIdLabel.setText('N/A')

        outputs = oq_models.Output.objects.filter(oq_job=83)
        mean_loss_maps = [o.loss_map for o in outputs
                          if o.output_type == 'loss_map'
                          and o.loss_map.statistics == 'mean']

        # Just display the first one for now (poE = 0.01)
        # TODO: provide a dropdown selector to choose which poe level to show
        loss_map = mean_loss_maps[0]

        # order assets by location
        locations = {}
        for asset in loss_map:
            # asset.location (of type GEOSGeometry) does not implement __cmp__
            (x, y) = asset.location
            locations.setdefault((x, y), []).append(asset)

        # sum losses for all assets at a specific location
        losses = [{'name': assets[0].asset_ref,
                   'loss': sum(a.value for a in assets),
                   'location': loc} for (loc, assets) in locations.items()]
        self.loss_layer.set_losses(losses)
        extent = self.loss_layer.extent()
        extent.scale(1.1)
        self.ui.mapWidget.setExtent(extent)


class ForecastsWindow(QtGui.QDialog):

    def __init__(self, atls_core, **kwargs):
        QtGui.QDialog.__init__(self, **kwargs)
        self.logger = logging.getLogger(__name__)

        # References
        self.atls_core = atls_core
        self.fc_history_model = None

        # Setup the user interface
        self.ui = Ui_ForecastsWindow()
        self.ui.setupUi(self)

        # Presenters for the main window components (the tabs)
        tab_classes = [IsTabPresenter, HazardTabPresenter, RiskTabPresenter]
        self.tab_presenters = [Klass(self.ui) for Klass in tab_classes]

        # Connect essential signals
        # ... from the core
        self.atls_core.engine.state_changed.\
            connect(self.on_engine_state_change)
        self.atls_core.project_loaded.connect(self.on_project_load)

        if self.atls_core.project is not None:
            self._load_project_data(self.atls_core.project)

    # Helpers

    def _load_project_data(self, project):
        self._observe_project_changes(project)
        # setup view model
        date_display = lambda x: x.t_run.ctime()
        roles = {
            Qt.DisplayRole: date_display
        }
        self.fc_history_model = EventListModel(project.forecast_history, roles)
        self.ui.forecastListView.setModel(self.fc_history_model)
        # observe selection changes
        fc_selection = self.ui.forecastListView.selectionModel()
        fc_selection.selectionChanged.connect(self.on_fc_selection_change)

    def _observe_project_changes(self, project):
        # Make sure we get updated on project changes
        project.will_close.connect(self.on_project_will_close)
        project.project_time_changed.connect(self.on_project_time_change)

    # Display update methods for individual window components with
    # increasing granularity (i.e. top level methods at the top)

    def _refresh_forecast_list(self):
        """
        Refresh the list of forecasts

        """
        self.fc_history_model.refresh()

    def _clear_all(self):
        for tab_presenter in self.tab_presenters:
            tab_presenter.present_forecast_result(None)

    # Handlers for signals from the core

    def on_project_will_close(self, _):
        self._clear_all()
        fc_selection = self.ui.forecastListView.selectionModel()
        fc_selection.selectionChanged.disconnect(self.on_fc_selection_change)
        self.ui.forecastListView.setModel(None)
        self.fc_history_model = None

    def on_project_time_change(self, t):
        pass

    def on_engine_state_change(self):
        pass

    def on_project_load(self, project):
        """
        :param project: ATLS project
        :type project: AtlsProject

        """
        self._load_project_data(project)

    # Handlers for signals from the UI

    def on_fc_selection_change(self, selection):
        idx = selection.indexes()
        if len(idx) != 1:
            fc = None
        else:
            fc = self.fc_history_model.event_history[idx[0].row()]
        for tab_presenter in self.tab_presenters:
            tab_presenter.present_forecast_result(fc)

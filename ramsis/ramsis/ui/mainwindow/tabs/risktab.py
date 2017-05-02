# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2015, SED (ETH Zurich)

"""

import os
from PyQt4 import QtGui
from qgis.core import QgsVectorLayer, QgsMapLayerRegistry, QgsRectangle
from qgis.gui import QgsMapCanvasLayer
from tabs import TabPresenter
from ui.mainwindow.qgislayers import RamsisLossPoeLayer

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

        # Commented out for testing without QGIS initialization
        #self.loss_layer = RamsisLossPoeLayer('Loss')
        #layers.append(self.loss_layer)

        # Set layers

        canvas_layers = [QgsMapCanvasLayer(l) for l in layers]
        self.ui.mapWidget.setExtent(QgsRectangle(5.6, 45.6, 10.8, 47.5))
        self.ui.mapWidget.setLayerSet(canvas_layers)

    def refresh(self):
        # FIXME: use new data model
        pass
        # self.logger.info('refreshing risk')
        # if self.presented_forecast:
        #     calc_id = self.presented_forecast.risk_oq_calc_id
        # else:
        #     calc_id = None
        # if calc_id is not None:
        #     self.ui.riskCalcIdLabel.setText(str(calc_id))
        # else:
        #     self.ui.riskCalcIdLabel.setText('N/A')

        # outputs = oq_models.Output.objects.filter(oq_job=83)
        # mean_loss_maps = [o.loss_map for o in outputs if
        #                   o.output_type == 'loss_map' and
        #                   o.loss_map.statistics == 'mean']
        #
        # # Just display the first one for now (poE = 0.01)
        # # TODO: provide a dropdown selector to choose which poe level to show
        # loss_map = mean_loss_maps[0]
        #
        # # order assets by location
        # locations = {}
        # for asset in loss_map:
        #     # asset.location (of type GEOSGeometry)
        #     # does not implement __cmp__
        #     (x, y) = asset.location
        #     locations.setdefault((x, y), []).append(asset)
        #
        # # sum losses for all assets at a specific location
        # losses = [{'name': assets[0].asset_ref,
        #            'loss': sum(a.value for a in assets),
        #            'location': loc} for (loc, assets) in locations.items()]
        # self.loss_layer.set_losses(losses)
        # extent = self.loss_layer.extent()
        # extent.scale(1.1)
        # self.ui.mapWidget.setExtent(extent)
# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

from PyQt4.QtCore import QVariant, Qt
from qgis.core import QgsVectorLayer, QgsField, QgsFeature, QgsGeometry, \
                      QgsPoint, QgsSingleSymbolRendererV2, QgsSymbolV2, \
                      QgsSimpleMarkerSymbolLayerV2


class AtlsDataPointsLayer(QgsVectorLayer):

    def __init__(self, name):
        super(AtlsDataPointsLayer, self).__init__('Point', name, 'memory')


class AtlsLossPoeLayer(AtlsDataPointsLayer):

    def __init__(self, name):
        super(AtlsLossPoeLayer, self).__init__(name)

        pr = self.dataProvider()
        pr.addAttributes([QgsField('name', QVariant.String),
                          QgsField('loss', QVariant.Double),
                          QgsField('size', QVariant.Double)])

        symbol = QgsSymbolV2.defaultSymbol(self.geometryType())
        symbol.setColor(Qt.green)
        renderer = QgsSingleSymbolRendererV2(symbol)
        #renderer.setSizeScaleField('size')
        #renderer.setSizeScaleField('size')
        self.setRendererV2(renderer)

    def set_losses(self, losses):
        """
        Set losses to display on the layer

        :param losses: list of dicts containing at least 'name', 'location' (a
            lon, lat tuple), 'loss' and 'poE' (probability of exceedance)

        """
        pr = self.dataProvider()

        max_loss = max(l['loss'] for l in losses)
        scale = 10.0 / max_loss
        features = []
        for loss in losses:
            f = QgsFeature()
            f.setGeometry(QgsGeometry.fromPoint(QgsPoint(*loss['location'])))
            loss_val = loss['loss']
            f.setAttributes([loss['name'], loss_val, 4.0])
            features.append(f)

        pr.addFeatures(features)
        self.updateExtents()

    def clear(self):
        self.dataProvider().deleteFeatures(self.allFeatureIds())
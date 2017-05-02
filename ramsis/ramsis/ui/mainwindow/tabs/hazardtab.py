# -*- encoding: utf-8 -*-
"""
Short Description

Long Description
    
Copyright (C) 2015, SED (ETH Zurich)

"""

from PyQt4.QtCore import QThread
from tabs import TabPresenter


class HazardTabPresenter(TabPresenter):
    """
    Handles the Hazard tabs content

    """

    def refresh(self):
        # FIXME: use new data model
        pass
        # self.logger.info('refreshing hazard on thread {}'
        #                  .format(QThread.currentThread().objectName()))
        # calc_id = None
        # if self.presented_forecast:
        #     calc_id = self.presented_forecast.hazard_oq_calc_id
        # if calc_id is not None:
        #     self.ui.hazCalcIdLabel.setText(str(calc_id))
        # else:
        #     self.ui.hazCalcIdLabel.setText('N/A')

        # outputs = oq_models.Output.objects.filter(oq_job=calc_id)
        #
        # hazard_curves = (o.hazard_curve for o in outputs
        #                  if o.output_type == 'hazard_curve')
        #
        # imls = None
        # for hc in hazard_curves:
        #     if hc.imt != 'MMI':
        #         # we only support mmi for now
        #         # TODO: show selection box for all IMTs
        #         continue
        #
        #     # extract IMLs once
        #     if imls is None:
        #         imls = hc.imls
        #
        #     # extract x, y, poes
        #     x_y_poes = oq_models.HazardCurveData.objects.all_curves_simple(
        #         filter_args=dict(hazard_curve=hc.id))
        #
        #     x, y, poes = next(x_y_poes)  # there should be only one
        #
        #     if hc.statistics == 'mean':
        #         pen = QtGui.QPen(Qt.red)
        #     elif hc.statistics == 'quantile':
        #         pen = QtGui.QPen(Qt.green)
        #     else:
        #         pen = QtGui.QPen(Qt.white)
        #
        #     self.ui.hazPlot.plot(imls, poes, pen=pen)
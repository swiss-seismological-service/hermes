# Atlas
# Copyright (C) 2013 Lukas Heiniger

class EffectEstimator(object):
    """
    Estimates effects for seismic events

    """

    def __init__(self, building_catalog, cost_function, ground_motion_predictor):
        self.building_catalog = building_catalog
        self.cost_function = cost_function
        self.ground_motion_predictor = ground_motion_predictor

    def estimate_effects_for_event(self, event):
        pass

class HYDWSCatalogImporter:
    def __init__(self, catalog):
        self.catalog = catalog

    def __iter__(self):
        for event in self.catalog:
            date = event.time
            row = {
                'flow_dh': event.bottomHoleFlowRate,
                'flow_xt': event.topHoleFlowRate,
                'pr_dh': event.bottomHolePressure,
                'pr_xt': event.topHolePressure
            }
            yield (date, row)

from datetime import datetime


class HYDWSCatalogImporter:
    def __init__(self, catalog):
        self.catalog = catalog

    def __iter__(self):
        for event in self.catalog:
            date = event['time']['value']
            date = datetime.strptime(date, '%Y-%m-%dT%H:%M:%S')
            row = {
                'flow_dh': event['bottomHoleFlowRate']['value'],
                'flow_xt': event['topHoleFlowRate']['value'],
                'pr_dh': event['bottomHolePressure']['value'],
                'pr_xt': event['topHolePressure']['value']
            }
            yield (date, row)

import json

from flask import request
from flask_restful import Resource

from data.modelresultslayer import ModelResultsLayer
from data.modelresultsitem import ModelResultsItem
from model.common import ModelOutput
from data.store import Store
from data.ormbase import OrmBase


class Rj(Resource):
    store = Store("sqlite:///db.sqlite", OrmBase)

    def post(self):
        data = json.loads(request.form["data"])

        model_output = ModelOutput(None, None, None)
        model_output.deserialize(data["model_output"])

        item = self._get_model_results_item(model_output)
        layer = ModelResultsLayer(self.store, ModelResultsItem)
        layer.add(item, persist=True)

    @staticmethod
    def _get_model_results_item(model_output):
        r = model_output.cum_result
        rate = r.rate if r else None
        b_val = r.b_val if r else None
        prob = r.prob if r else None

        item = ModelResultsItem(
            model_output.failed,
            model_output.failure_reason,
            model_output.t_run,
            model_output.dt,
            rate,
            b_val,
            prob
        )

        return item


class RjId(Resource):
    store = Store("sqlite:///db.sqlite", OrmBase)

    def get(self):
        layer = ModelResultsLayer(self.store, ModelResultsItem)
        next_id = layer.get_next_id()
        return next_id

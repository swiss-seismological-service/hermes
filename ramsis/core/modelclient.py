import json
import requests


class ModelClient(object):
    def __init__(self, model, settings):
        self.model = model
        key = 'worker/%s_url' % self.model['model']
        self.url = settings.value(key)

    def run(self, model_input):
        data = {
            "model_input": model_input.serialize(),
            "parameters": self.model["parameters"]
        }

        requests.post(self.url, data={"data": json.dumps(data)})

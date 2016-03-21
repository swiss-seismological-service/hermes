import json
import requests


class ModelClient(object):
    def __init__(self, model, settings):
        self.model = model
        key = 'worker/%s_url' % self.model['model']
        self.url = settings.value(key)
        self.job_id = None

    def run(self, model_input):
        data = {
            "model_input": model_input.serialize(),
            "parameters": self.model["parameters"]
        }

        r = requests.post(self.url, data={"data": json.dumps(data)})
        self.job_id = ''.join([c for c in r.content if c.isdigit()])

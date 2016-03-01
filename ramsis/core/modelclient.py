import json
import requests


class ModelClient(object):
    def __init__(self, model, settings):
        self.model = model
        key = 'worker/%s_url' % self.model['model']
        self.url = settings.value(key)

    def run(self, model_input):
        datetime_format = "%Y-%m-%dT%H:%M:%S"
        data = {
            "data": model_input.serialize(datetime_format),
            "datetime_format": datetime_format,
            "parameters": self.model["parameters"]
        }

        response = requests.post(self.url, data={"data": json.dumps(data)})

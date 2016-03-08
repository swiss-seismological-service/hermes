from multiprocessing import Process

from model.common import ModelInput
from model.rj import Rj

_jobs = {}


def run(request_data, job_id):
    p = Process(target=_run, args=(request_data, job_id))
    p.start()


def get_status(job_id):
    global _jobs

    return _jobs[job_id]['status']


def _run(request_data, job_id):
    global _jobs

    model_input = ModelInput(None)
    model_input.deserialize(request_data["model_input"])

    model = Rj(**request_data["parameters"])
    _jobs[job_id] = {'model': model, 'status': 'processing'}
    model.finished.connect(_on_model_finished)
    model.prepare_run(model_input, job_id)
    model.run()


def _on_model_finished(job_id):
    global _jobs

    _jobs[job_id]['status'] = 'finished'

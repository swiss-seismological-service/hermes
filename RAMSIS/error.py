
class RamsisError(Exception):
    """General error for RAMSIS"""


class RemoteWorkerError(RamsisError):
    """Error recieved back from Remote Worker that calls seismicity model"""


class ModelFailedError(RamsisError):
    """Error recieved back from seismicity model"""


class ModelNoForecastError(RamsisError):
    """Seismicity model completed sucessfully but returned an empty forecast"""


class ModelNotFinished(Exception):
    """Raised to allow retry of the task if the model is still processing"""

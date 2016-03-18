from sqlalchemy import Column, Integer, Float, DateTime, Boolean, String

from ormbase import OrmBase


class ModelResultsItem(OrmBase):
    # ORM declarations
    __tablename__ = 'modelresultsitems'
    id = Column(Integer, primary_key=True)
    failed = Column(Boolean)
    failure_reason = Column(String)
    t_run = Column(DateTime)
    dt = Column(Float)
    rate = Column(Float)
    b_val = Column(Float)
    prob = Column(Float)

    # Data attributes (required for flattening)
    data_attrs = ['failed', 'failure_reason', 't_run', 'dt', 'rate', 'b_val',
                  'prob']

    def __init__(self, failed, failure_reason, t_run, dt, rate, b_val, prob):
        self.failed = failed
        self.failure_reason = failure_reason
        self.t_run = t_run
        self.dt = dt
        self.rate = rate
        self.b_val = b_val
        self.prob = prob

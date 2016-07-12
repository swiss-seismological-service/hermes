import flask
import flask.ext.sqlalchemy
import flask.ext.restless

from settings import settings

app = flask.Flask(__name__)
app.config['DEBUG'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = settings['database_path']
db = flask.ext.sqlalchemy.SQLAlchemy(app)


class ModelResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    failed = db.Column(db.Boolean)
    failure_reason = db.Column(db.String)
    t_run = db.Column(db.DateTime)
    dt = db.Column(db.Float)
    rate = db.Column(db.Float)
    b_val = db.Column(db.Float)
    prob = db.Column(db.Float)


db.create_all()
manager = flask.ext.restless.APIManager(app, flask_sqlalchemy_db=db)
manager.create_api(ModelResult, methods=['GET', 'POST', 'PUT'])
app.run(port=5001)

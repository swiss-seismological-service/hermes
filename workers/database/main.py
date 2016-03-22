from flask import Flask
from flask_restful import Api

from resources import Rj, RjId

app = Flask(__name__)
api = Api(app)
api.add_resource(Rj, '/rj')
api.add_resource(RjId, '/rj/next_job_id')

if __name__ == '__main__':
    app.run(debug=True, port=5001)

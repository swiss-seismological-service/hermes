from flask import Flask
from flask_restful import Api

from resources import Jobs

app = Flask(__name__)
api = Api(app)
api.add_resource(Jobs, '/<string:job_id>')

if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask
from flask_restful import Api

from resources import Run

app = Flask(__name__)
api = Api(app)
api.add_resource(Run, '/run')

if __name__ == '__main__':
    app.run(debug=True)

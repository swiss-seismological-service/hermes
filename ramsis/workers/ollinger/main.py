from flask import Flask
from flask_restful import Api

from resources import Run


def main():
    app = Flask(__name__)
    api = Api(app)
    api.add_resource(Run, '/run')

    app.run(host='0.0.0.0', port=8080, debug=True)


if __name__ == '__main__':
    main()

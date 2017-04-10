import json

from flask import Flask, request

import worker

app = Flask(__name__)


@app.route("/run", methods=["POST"])
def run():
    result = worker.run(json.loads(request.form["data"]))
    return str(result)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port="8080")

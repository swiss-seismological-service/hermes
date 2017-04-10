from datetime import datetime
import csv
import json
import os
import subprocess

from flask import request
from flask_restful import Resource


class Run(Resource):
    model_path = "C:\RAMSIS\Worker\Simulation_Test\start_simulation.bat"

    def post(self):
        try:
            print 'Model run started'
            data = json.loads(request.form["data"])
            print 'Writing seismic catalog...'
            self._write_seismic_catalog(data)
            print 'Running...'
            p = subprocess.Popen(self.model_path,
                                 cwd=os.path.split(self.model_path)[0])
            p.communicate()
            print 'Done'
        except:
            return 500
        return 200

    def _write_seismic_catalog(self, data):
        with open('Simulation_Test\SeismicCatalog_Measured.csv', 'wb')\
                as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            writer.writerow(["Time", "Offset-X(m)", "Offset-Y(m)",
                             "Offset-Z(m)", "Local magnitude"])
            events = data["forecast"]["input"]["input_catalog"]
            events = events["seismic_events"]
            for e in events:
                d = datetime.strptime(e["date_time"], '%Y-%m-%dT%H:%M:%S+00:00')
                e["date_time"] = d.strftime('%d.%m.%Y %H:%M:%S.0000')
                row = [e[key] for key in ["date_time", "x", "y", "z",
                                          "magnitude"]]
                writer.writerow(row)

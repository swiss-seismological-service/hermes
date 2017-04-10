import csv
from datetime import datetime
import os
import subprocess

MODEL_PATH = "C:\RAMSIS\Worker\Simulation_Test\start_simulation.bat"


def run(data):
    try:
        print 'Writing seismic catalog...'
        _write_seismic_catalog(data)
        print 'Running model...'
        p = subprocess.Popen(MODEL_PATH, cwd=os.path.split(MODEL_PATH)[0])
        p.communicate()
        print 'Model run complete'
    except:
        return 500
    return 200


def _write_seismic_catalog(data):
    with open('Simulation_Test\SeismicCatalog_Measured.csv', 'wb') as csvfile:
        writer = csv.writer(csvfile, delimiter=';')
        writer.writerow(["Time", "Offset-X(m)", "Offset-Y(m)", "Offset-Z(m)",
                         "Local magnitude"])
        for e in data["forecast"]["input"]["input_catalog"]["seismic_events"]:
            d = datetime.strptime(e["date_time"], '%Y-%m-%dT%H:%M:%S+00:00')
            e["date_time"] = d.strftime('%d.%m.%Y %H:%M:%S.0000')
            row = [e[key] for key in ["date_time", "x", "y", "z", "magnitude"]]
            writer.writerow(row)

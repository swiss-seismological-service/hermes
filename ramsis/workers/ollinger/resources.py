from datetime import datetime
import csv
import json
import os
import subprocess
import glob

from flask import request
from flask_restful import Resource


class Run(Resource):
    model_dir = 'C:\RAMSIS\Worker\Simulation_Test'
    model_file = os.path.join(model_dir, 'start_simulation.bat')
    seismic_catalog_files = glob.glob(os.path.join(
        model_dir, 'SeismicCatalog_000[0-9][0-9].csv'))

    def post(self):
        try:
            print('Model run started')
            data = json.loads(request.form['data'])
            print('Writing seismic catalog...')
            self._write_seismic_catalog(data)
            print('Running...')
            p = subprocess.Popen(self.model_file, cwd=self.model_dir)
            p.communicate()
            print('Done')
        except:
            return 500
        return 200

    def get(self):
        try:
            for catalog in self.seismic_catalog_files:
                with open(catalog) as f:
                    pass  # TODO: calculate statistics
            model_result = json.dumps({
                'skill_test': None,
                'failed': False,
                'model_name': '',
                'rate_prediction': None,
                'failure_reason': ''
            })
            return model_result
        except:
            return None

    def _write_seismic_catalog(self, data):
        with open('Simulation_Test\SeismicCatalog_Measured.csv', 'wb')\
                as csvfile:
            writer = csv.writer(csvfile, delimiter=';')
            writer.writerow(['Time', 'Offset-X(m)', 'Offset-Y(m)',
                             'Offset-Z(m)', 'Local magnitude'])
            events = data['forecast']['input']['input_catalog']
            events = events['seismic_events']
            try:
                for e in events:
                    d = datetime.strptime(e['date_time'],
                                          '%Y-%m-%dT%H:%M:%S+00:00')
                    e['date_time'] = d.strftime('%d.%m.%Y %H:%M:%S.0000')
                    row = [e[key] for key in ['date_time', 'x', 'y', 'z',
                                              'magnitude']]
                    writer.writerow(row)
            except TypeError:
                print('Could not write catalog: no seismic events')
                return

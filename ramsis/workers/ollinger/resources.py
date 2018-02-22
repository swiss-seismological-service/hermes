from datetime import datetime
import csv
import os
import subprocess
import glob

from flask import request
from flask import current_app as app
from flask_restful import Resource

import numpy as np


current_process = None


class Run(Resource):
    model_dir = 'C:\RAMSIS\Worker\Simulation_Test'
    model_file = os.path.join(model_dir, 'start_simulation.bat')
    seismic_catalog_files = glob.glob(os.path.join(
        model_dir, 'SeismicCatalog_000[0-9][0-9].csv'))

    def post(self):
        global current_process
        app.logger.debug('Received post request')
        if current_process and current_process.poll() is None:
            msg = 'Previous run has not finished yet'
            app.logger.error(msg)
            return msg, 503

        try:
            app.logger.info('Starting model')
            data = request.json
            _write_seismic_catalog(data)
            current_process = subprocess.Popen(self.model_file,
                                               cwd=self.model_dir)
        except OSError as e:
            msg = 'Failed to launch model: {}'.format(repr(e))
            app.logger.error(msg)
            current_process = None
            return msg, 500
        except (ValueError, TypeError, KeyError) as e:
            msg = 'Input data error: {}'.format(repr(e))
            app.logger.error(msg)
            return msg, 400

        return {'status': 'running'}, 202  # Accepted

    def get(self):
        app.logger.debug('Received get request')
        if current_process is None:
            app.logger.debug('No model running')
            return '', 204  # No Content

        return_code = current_process.poll()
        if return_code is None:
            app.logger.debug('Still running')
            return {'status': 'running'}, 202  # Accepted
        elif return_code == 0:
            app.logger.debug('Assembling results')
            try:
                for catalog in self.seismic_catalog_files:
                    with open(catalog) as f:
                        pass  # TODO: calculate statistics
                return {
                    'status': 'complete',
                    'result': {
                        'rate_prediction': self._eval_results()
                    }
                }
            except Exception as e:
                msg = 'Failed to process result: {}'.format(repr(e))
                app.logger.error(msg)
                return msg, 500
        else:
            app.logger.debug('Model failed')
            return {'status': 'error'}, 202  # Accepted

    def _eval_results(self):
        all_results = []
        for catalog in self.seismic_catalog_files:
            with open(catalog) as f:
                reader = csv.reader(f, delimiter=';')
                next(reader)  # skip header
                mags = [float(row[1]) for row in reader]
                gr = _estimate_gr_params(mags)
                app.logger.debug('Stats (a, b, std) for {}: {}'
                                 .format(catalog, gr))
                all_results.append(gr)
        gr = np.mean(all_results, 0).tolist()
        app.logger.debug('Mean {}:'.format(gr))
        return gr


def _write_seismic_catalog(data):
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
            app.logger('Could not write catalog: no seismic events')
            raise


def _estimate_gr_params(magnitudes, mc=None):
    """
    Estimates the Gutenberg Richter parameters based on a list of magnitudes.
    The magnitudes list is expected to contain no values below mc

    :param mc: Magnitude of completeness. If not given, the smallest value in
        magnitudes is used as mc
    :param magnitudes: List of magnitudes
    :returns: Gutenberg Richter parameter estimates as tuple (a, b, std_b)

    """
    mags = np.array(magnitudes)
    if mc is None:
        mc = mags.min()
    else:
        mags = mags[mags >= mc]
    n = mags.size
    m_mean = mags.mean()
    b = 1 / (np.log(10) * (m_mean - mc))
    a = np.log10(n) + b * mc
    std_b = 2.3 * np.sqrt(sum((mags - m_mean) ** 2) / (n * (n - 1))) * b ** 2
    return a, b, std_b

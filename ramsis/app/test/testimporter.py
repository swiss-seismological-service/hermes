# -*- encoding: utf-8 -*-
"""
Unit test for the EventImporter class

Copyright (C) 2013, ETH Zurich - Swiss Seismological Service SED

"""

import unittest
from datetime import timedelta, datetime

from core.datasources import CsvEventImporter


class Import(unittest.TestCase):

    def test_import_abs_tab(self):
        """
        Test if the csv import works as expected with a file that is tab
        delimited and contains absolute dates

        """

        # Prepare expected data
        base_date = datetime(2013, 3, 15)
        expected = []
        for i in range(3):
            date = base_date + timedelta(seconds=i)
            row = {'flow_dh': (-82.0 - i * 0.1),
                   'flow_xt': (132.0 + i * 0.1),
                   'pr_dh': (719 + i * 0.1),
                   'pr_xt': (269 + i * 0.1)}
            expected.append((date, row))

        with open('test/resources/test_hydr.csv', 'rb') as f:
            # Create unit under test
            importer = CsvEventImporter(f, delimiter='\t')
            importer.date_format = '%Y-%m-%dT%H:%M:%S'

            # Since dates are absolute, the importer should not
            # expect a base date
            self.assertFalse(importer.expects_base_date)

            # Check if imported data is correct
            i = 0
            for date, row in importer:
                expected_date, expected_row = expected[i]
                self.assertEqual(date, expected_date)
                for key in expected_row.keys():
                    self.assertEqual(float(row[key]), expected_row[key])
                i += 1

    def test_import_rel_spc(self):
        """
        Test if the csv import works as expected with a file that is space
        delimited and contains relative dates

        """

        # Prepare expected data
        base_date = datetime(2013, 3, 15)
        date1 = base_date + timedelta(days=0.17)
        row1 = {'mag': 0.4, 'lat': 47.5, 'lon': 7.5}
        date2 = base_date + timedelta(days=0.23)
        row2 = {'mag': 0.8, 'lat': 47.6, 'lon': 7.6}
        date3 = base_date + timedelta(days=0.26)
        row3 = {'mag': 0.45, 'lat': 47.7, 'lon': 7.7}

        expected = [(date1, row1), (date2, row2), (date3, row3)]

        with open('test/resources/test_catalog.csv', 'rb') as f:
            # Create unit under test
            importer = CsvEventImporter(f)
            importer.base_date = base_date

            # Since dates are relative, the importer should expect a base date
            self.assertTrue(importer.expects_base_date)

            # Check if imported data is correct
            i = 0
            for date, row in importer:
                expected_date, expected_row = expected[i]
                self.assertEqual(date, expected_date)
                for key in expected_row.keys():
                    self.assertEqual(float(row[key]), expected_row[key])
                i += 1


if __name__ == '__main__':
    unittest.main()

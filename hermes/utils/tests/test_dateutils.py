from datetime import datetime

from hermes.utils.dateutils import generate_date_ranges


def test_generate_date_ranges():
    starttime = datetime(2020, 6, 15, 12, 0)
    endtime = datetime(2023, 3, 20, 15, 0)

    date_ranges = generate_date_ranges(starttime, endtime)

    assert date_ranges == [
        (datetime(2020, 6, 15, 12, 0), datetime(2020, 12, 31, 23, 59, 59)),
        (datetime(2021, 1, 1, 0, 0), datetime(2021, 12, 31, 23, 59, 59)),
        (datetime(2022, 1, 1, 0, 0), datetime(2022, 12, 31, 23, 59, 59)),
        (datetime(2023, 1, 1, 0, 0), datetime(2023, 3, 20, 15, 0)),
    ]

    starttime = datetime(2020, 6, 15, 12, 0)
    endtime = datetime(2020, 12, 15, 12, 0)

    date_ranges = generate_date_ranges(starttime, endtime)

    assert date_ranges == [
        (datetime(2020, 6, 15, 12, 0), datetime(2020, 12, 15, 12, 0))]

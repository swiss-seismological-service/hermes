import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone


def generate_date_ranges(starttime, endtime):
    date_ranges = []

    # Check if the starttime and endtime are more than a year apart
    if endtime > starttime + timedelta(days=365):
        # First range: starttime to the end of the year
        first_year_end = datetime(
            starttime.year + 1, 1, 1) - timedelta(seconds=1)
        date_ranges.append((starttime, first_year_end))

        # Intermediate full-year ranges
        current_start = first_year_end + timedelta(seconds=1)
        while current_start + timedelta(days=365) < endtime:
            next_year_end = datetime(
                current_start.year + 1, 1, 1) - timedelta(seconds=1)
            date_ranges.append((current_start, next_year_end))
            current_start = next_year_end + timedelta(seconds=1)

        # Final range: start of the last year to endtime
        date_ranges.append((current_start, endtime))

    else:
        # If the dates are not more than a year apart,
        # just return the original range
        date_ranges.append((starttime, endtime))

    return date_ranges


def local_to_utc(dt: datetime) -> datetime:
    # Check if the datetime object is naive (no timezone info)
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)

    # Create a timezone offset object
    local_offset = timedelta(seconds=time.localtime(dt.timestamp()).tm_gmtoff)

    # Set the timezone info to local timezone
    local_dt = dt.replace(tzinfo=timezone(local_offset))

    # Convert to UTC
    utc_dt = local_dt.astimezone(timezone.utc)

    return utc_dt.replace(tzinfo=None)


def local_to_utc_dict(dic: dict) -> dict:
    new_dict = deepcopy(dic)
    for key, value in new_dict.items():
        # try converting string value to datetime object
        try:
            dt = local_to_utc(datetime.fromisoformat(value))
            new_dict[key] = dt.isoformat()
        except BaseException:
            pass
    return new_dict

import time
from copy import deepcopy
from datetime import datetime, timedelta, timezone


def generate_date_ranges(
        starttime: datetime,
        endtime: datetime,
        resolution: int = 365) -> list[tuple[datetime, datetime]]:
    """
    Generate date ranges for a given time period.

    Args:
        starttime: Start time of the period.
        endtime: End time of the period.
        resolution: Maximum duration of each range in days.

    Returns:
        List of date ranges.
    """
    intervals = []

    # Start iterating from starttime
    current_start = starttime

    # Loop until current_start reaches or exceeds endtime
    while current_start < endtime:
        # Calculate the end of the current interval
        current_end = current_start + timedelta(days=resolution)

        # If current_end exceeds endtime, adjust it to endtime
        if current_end > endtime:
            current_end = endtime

        # Add the (start, end) tuple to intervals
        intervals.append((current_start, current_end))

        # Move to the next interval
        current_start = current_end

    return intervals


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

from datetime import datetime, timedelta


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

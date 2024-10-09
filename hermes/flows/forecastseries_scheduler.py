# import asyncio
from datetime import datetime, timedelta

from hermes.schemas import ForecastSeries

# from prefect.client.orchestration import get_client
# from prefect.client.schemas.schedules import RRuleSchedule


class ForecastSeriesScheduler:
    def __init__(self, forecastseries: ForecastSeries):
        assert forecastseries.forecast_starttime is not None
        assert forecastseries.forecast_interval is not None
        assert forecastseries.forecast_endtime or \
            forecastseries.forecast_duration

        self.forecastseries = forecastseries
        self.start = forecastseries.forecast_starttime
        self.end = forecastseries.forecast_endtime
        self.interval = forecastseries.forecast_interval
        self.duration = forecastseries.forecast_duration
        self.now = datetime.now()

        self.past_forecasts = []
        self.set_past_forecasts()

    def set_past_forecasts(self):
        # If the start time is in the future, we don't have any past forecasts
        if self.start > self.now:
            return None

        # the overall end for past forecasts
        if self.end is not None and self.end < self.now:
            past_end = self.end
        else:
            past_end = self.now

        # calculate the intervals for past forecasts
        total_seconds = int((past_end - self.start).total_seconds())
        intervals = range(0, total_seconds + 1, self.interval)

        for i in intervals:
            interval_start = self.start + timedelta(seconds=i)

            # if the forecast has a duration, calculate the end times
            if self.duration:
                interval_end = interval_start + \
                    timedelta(seconds=self.duration)
            # if no duration is specified, use the overall end time
            else:
                interval_end = self.end

            if not interval_end == interval_start:
                self.past_forecasts.append((interval_start, interval_end))

        next_start = self.past_forecasts[-1][0] + \
            timedelta(seconds=self.interval)

        if self.end is None or next_start < self.end:
            self.start = next_start

    def run(self):
        pass


# input to forecastflowrunner:
# forecastseries: UUID,
# starttime: datetime | None = None,
# endtime: datetime | None = None

# 1. get start and endtime for each forecast in the past
# 2. get the next starttime in the future
# 3. schedule ForecastFlowRunner with the next starttime
#    and according to the parameters from the forecastseries


# async def add_schedule_to_deployment():
#     async with get_client() as client:
#         deployment = await client.read_deployment(
#             "your-flow-name/your-deployment-name")

#         # Calculate start and end times
#         start_time = datetime.now().replace(hour=16, minute=0, second=0,
#                                             microsecond=0) + timedelta(days=1)
#         end_time = start_time + \
#             timedelta(days=(4 - start_time.weekday() + 7) % 7)  # Next Friday
#         end_time = end_time.replace(hour=17, minute=0, second=0, microsecond=0)

#         # Create RRule schedule
#         rrule = f"FREQ=MINUTELY;INTERVAL=30;DTSTART={start_time.isoformat()}" \
#                 f";UNTIL={end_time.isoformat()}"
#         new_schedule = RRuleSchedule(rrule=rrule)

#         # Add the new schedule to the deployment
#         await client.create_deployment_schedule(
#             deployment_id=deployment.id,
#             schedule=new_schedule
#         )

# Run the async function

# asyncio.run(add_schedule_to_deployment())

# import asyncio
from datetime import datetime, timedelta

from dateutil.rrule import SECONDLY, rrule
from prefect.client.orchestration import get_client
from prefect.client.schemas.schedules import RRuleSchedule

from hermes.schemas import ForecastSeries


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
        self._set_past_forecasts()

        self._create_schedule()

    def _set_past_forecasts(self):
        """
        If the forecast has a start time in the past, calculate the past
        forecast start and endtimes.
        """
        # If the start time is in the future, we don't have any past forecasts
        if self.start > self.now:
            return None

        # if the endtime lies in the past, we only want to calculate
        # past forecasts up to the endtime
        if self.end is not None and self.end < self.now:
            past_end = self.end
        # otherwise we calculate past forecasts up to the current time
        else:
            past_end = self.now

        # if no duration is specified, we want to avoid creating a forecast
        # which starts at the same time as the endtime
        if self.duration is None:
            past_end -= timedelta(seconds=1)

        rrule_past = rrule(freq=SECONDLY, interval=self.interval,
                           dtstart=self.start, until=past_end)

        self.past_forecasts = list(rrule_past)

    def _create_schedule(self):

        if self.end is not None and self.end < self.now:
            return None

        if self.start < self.now:
            rrule_full = rrule(freq=SECONDLY, interval=self.interval,
                               dtstart=self.start, until=self.end)
            self.start = rrule_full.after(self.now, inc=False)

        rrule_future = rrule(freq=SECONDLY, interval=self.interval,
                             dtstart=self.start, until=self.end)

        self.schedule = RRuleSchedule(rrule=str(rrule_future))

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
#         rrule = rrulestr('FREQ=WEEKLY;BYDAY=MO,WE,FR;UNTIL=20240730T040000Z')
#         # rrule = f"FREQ=MINUTELY;INTERVAL=30;DTSTART={start_time.isoformat()}" \
#         #         f";UNTIL={end_time.isoformat()}"
#         # new_schedule = RRuleSchedule(rrule=rrule)
#         new_schedule = construct_schedule(rrule=rrule)

#         # Add the new schedule to the deployment
#         await client.create_deployment_schedules(
#             deployment_id=deployment.id,
#             schedule=new_schedule
#         )

# Run the async function

# asyncio.run(add_schedule_to_deployment())

import asyncio
from datetime import datetime, timedelta, timezone

from dateutil.rrule import SECONDLY, rrule
from prefect import flow
from prefect.client.orchestration import get_client
from prefect.client.schemas.schedules import RRuleSchedule

from hermes.flows.forecastseries_scheduler import add_schedule_to_deployment


@flow(name="my-flow")
def my_flow():
    print("Flow is running!")


async def update_schedule(name):

    async with get_client() as client:
        deployment = await client.read_deployment_by_name(name)
        schedules = deployment.schedules

        new_schedule = rrule(freq=SECONDLY,
                             interval=10,
                             dtstart=datetime.now(timezone.utc)
                             + timedelta(seconds=10),
                             until=datetime.now(timezone.utc)
                             + timedelta(seconds=20))

        await client.update_deployment_schedule(
            deployment_id=deployment.id,
            schedule_id=schedules[0].id,
            schedule=RRuleSchedule(rrule=str(new_schedule))
        )


if __name__ == '__main__':
    name = "my-flow/my-flow"

    schedule = rrule(freq=SECONDLY,
                     interval=10,
                     dtstart=datetime.now(timezone.utc)
                     - timedelta(seconds=10),
                     until=datetime.now(timezone.utc) + timedelta(seconds=20))

    asyncio.run(add_schedule_to_deployment(name, schedule))

    # asyncio.run(update_schedule(name))

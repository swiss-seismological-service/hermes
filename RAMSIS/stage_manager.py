



from prefect import Client

client = Client()
client.create_flow_run(
    flow_id="d7bfb996-b8fe-4055-8d43-2c9f82a1e3c7",
    scheduled_start_time=pendulum.now().add(minutes=10)
)



# use flow_group_id for executing groups

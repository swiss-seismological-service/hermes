# RAMSIS Set-Up

#### .env file

An environment file needs to be set with the following variables. it should be located at the top directory in the rt-ramsis directory (same level as RAMSIS directory) and be called ''.env":

`POSTGRES_USER=postgres`
`POSTGRES_PASSWORD=ramsis`
`POSTGRES_SERVER=localhost`
`POSTGRES_PORT=5435`
`POSTGRES_DB=ramsis_test`



##### Test mode

There is a testing mode which accesses a different set of postgres credentials at ".env.test".  This is used when running the tests in ramsis and if the user would like to run something that doesn't touch the main database, this is a useful way to do that.

The test mode is defined by setting an environment variable within the terminal window that you run the various CLI commands, for example:

`export RAMSIS_TESTING_MODE=true`

To go back to using the main database, simply unset this variable or set it to false.

The .env.test file needs two sets of credentials, as the 'tester' user isn't set to have permissions to do tear down and set up of databases in the context of the tests. Please be aware that running pytest will destroy the database set here, setting a fresh one up for testing. 

.env.test:

`DEFAULT_USER=postgres`
`DEFAULT_DB=ramsis`
`DEFAULT_PASSWORD=ramsis`
`POSTGRES_PORT=5435`
`POSTGRES_SERVER=localhost`
`POSTGRES_USER=tester`
`POSTGRES_PASSWORD=test`
`POSTGRES_DB=ramsis_test_new`

The 'DEFAULT' variables are the ones that exist in .env, and the 'POSTGRES' variables are those that will be used when a command is run.





### Running Prefect

Prefect handles the managing, orchestration and deployment of tasks. A server and agent must be set up for RAMSIS to work. Describes below are the individual commands that can be run in a terminal window ad-hoc or better still, run with supervisord/systemd.

#### Prefect Server

The Prefect Server API instance needs to be running to manage the prefect tasks. More information may be found here:

https://docs.prefect.io/latest/guides/host/



`prefect server  start  --host 0.0.0.0 --port 4208`

Here I have set host to this to help with accessing the Prefect UI when running in a VM, and chosen a different port as the default one was already occupied.

The defaults can be viewed with `prefect config view --show-defaults`

and set with `prefect config set <variable>`

#### Prefect Agent

The Prefect Agent polls work from the Prefect Server and deploys flow runs (saves the runnable code for later usage)

https://docs.prefect.io/latest/concepts/agents/

`prefect agent  start "default" --api http://0.0.0.0:4208/api`

"default" is the name of the work queue in place that is currently hardcoded in RAMSIS/cli/utils.py in flow_deployment. There is scope to make this configurable if the need arises to have work queues where you can pause, set concurrency limits or priority ranking.

The api input is the address where the prefect server is running.

####  Supervisord

A plus of using this, is that it can be installed within your python environment with pip and uses a single configuration file to set up the running of both the agent and server. An example (That used on the ramsis-rise.ethz.ch machine) of this file can be found at the top level directory in the ramsis repo. The prefect agent/ server write to log files defined in the config.

#### Systemd



I followed this basic instruction along with some other additions:

https://discourse.prefect.io/t/how-to-run-a-prefect-2-worker-as-a-systemd-service-on-linux/1450

However, the current version of prefect contains a but that does not find a required library. Upgrading prefect changes the way that deployment is done, so for this to be possible a upgrade of the deployment in the CLI needs to be done.



#### Docker containers (forge specific)

There are two postgres docker containers running for the db for ramsis and the worker. There is a volume configured at /home/indu/docker/volumes/postgres.

rt-ramsis runs on port 5432

sfm-worker runs on port 5433



#### Worker

Once a database is created at postgresql://postgres:indu@localhost:5433/worker_forge_2022, the following commands are run:

`ramsis-sfm-worker-db-init --logging-conf worker/config/logging.conf  postgresql://postgres:indu@localhost:5433/worker_forge_2022`

`ramsis-sfm-worker-api --logging-conf worker/config/logging.conf --port 5007 postgresql://postgres:indu@localhost:5433/worker_forge_2022`





#### Configuration (forge specific)

The configuration for the forge 2022 rerun is under the top directory 'forge_2022'. The main configuration file config.json defines which files to use for initializing a forecastseries and project. Of course these configuration files can be used individually without the use of config.json as found in the user_guide.

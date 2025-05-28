![pypi](https://img.shields.io/pypi/v/rt-hermes)
[![PyPI - License](https://img.shields.io/pypi/l/rt-hermes)](https://pypi.org/project/rt-hermes/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/rt-hermes.svg)](https://pypi.org/project/rt-hermes/)
[![test](https://github.com/swiss-seismological-service/rt-hermes/actions/workflows/tests.yml/badge.svg)](https://github.com/swiss-seismological-service/rt-hermes/actions/workflows/tests.yml)
[![codecov](https://codecov.io/github/swiss-seismological-service/rt-hermes/graph/badge.svg?token=RVJFHYLBKA)](https://codecov.io/github/swiss-seismological-service/rt-hermes)

# RT-HERMES - *RealTime Hub for Earthquake foRecasts ManagEment and Scheduling*
©2025 ETH Zurich

## Overview
This project is under active development. The goal is to provide an orchestration and scheduling platform for earthquake forecast models. 

For v1 of the project, see the [gitlab repository](https://gitlab.seismo.ethz.ch/indu/rt-ramsis)

## Installation
This installation instruction is merely a recommendation for a user of the software. Depending on your preferences and knowledge, you are free to choose a different setup.


### 1. Install Docker
Follow the instructions [here](https://docs.docker.com/get-docker/)

### 2. Create a working directory with a Python virtual environment
Required Python version is 3.12
```
mkdir hermes-project && cd hermes-project
python3 -m venv env
source env/bin/activate
pip install -U pip wheel setuptools
```

### 3. Clone the repository into a subfolder
```
git clone https://github.com/swiss-seismological-service/hermes.git src/hermes
```

### 4. Install the required Python packages
```
pip install -e src/hermes
```

### 5. Start the Prefect Service
After the successful installation of Docker, you can start the Prefect service with the following command:
```
docker compose -f src/hermes/compose-prefect.yaml up -d
```
If you want to set a more secure password, you can pass it as an environment variable:
```
PREFECT_PASSWORD=mytopsecretpass docker compose -f src/hermes/compose-prefect.yaml up -d
```

### 5. Configure environment file
```
cp src/hermes/.env.example .env
```
As a quick test setup, the configuration works as is, but is not secure. Please change the credentials, ports and connection strings in the .env file.

### 6. Start the HERMES database services
```
docker compose --env-file .env -f src/hermes/compose-database.yaml up -d
```

### 7. Install the models
```
git clone https://gitlab.seismo.ethz.ch/indu/em1.git src/em1
git clone https://github.com/swiss-seismological-service/etas.git src/etas

pip install -e src/em1
pip install -e src/etas
```

### 8. Start with example configuration and data
```
cp -r src/hermes/examples .
```
Update the absolute path `fdsnws_url` in the `examples/induced/forecastseries.json` file to the path of the `examples/induced` folder.

### 9. Initialize the database
```
hermes db init
```
This only needs to be done once. In case you want to delete all data and start from scratch, you can run `hermes db purge` and then `hermes db init` again.

### 10. Load an example configuration
```
hermes projects create project_induced --config examples/induced/project.json
hermes forecastseries create fs_induced --config examples/induced/forecastseries.json --project project_induced
hermes injectionplans create default --forecastseries fs_induced --file examples/induced/multiply_template.json
hermes models create em1 --config examples/induced/model_config.json
```

The CLI can be used to interact with the HERMES service. For a list of available commands, run `hermes --help`. Most commands have a `--help` option to show the available options.

Most setting should be self-explanatory, but more information can be found in the [concepts documentation](https://github.com/swiss-seismological-service/hermes/blob/main/docs/concepts.md).

A more detailed of the InjectionPlan configuration can be found [here](https://github.com/swiss-seismological-service/hermes/blob/main/docs/injectionplan.md).

### 11. Run a single forecast using the CLI
```
hermes forecasts run fs_induced --start 2022-04-21T15:00:00 --end 2022-04-21T18:00:00 --local
```
This starts a single forecast directly on the local machine. 

### 12. (Optional) Schedule forecasts or execute "replays".
To use advanced features like scheduling, it is necessary to start a process which "serves" the forecastseries. 
```
hermes forecastseries serve fs_induced
```

Depending on your model, you need to control how many modelruns are executed in parallel, you can do that by specifying the `--concurrency-limit` option which is by default set to 3. Please consider, that also the requesting of the input data can become a limiting factor if you are requesting a lot of data at the same time (eg. requests to an FDSNWS).

```
hermes forecastseries serve fs_induced --concurrency-limit 1
```

Once this process is running, you can "send" a forecast to the service using the above command without the `--local` flag.  

```
hermes forecasts run fs_induced --start 2022-04-21T15:00:00 --end 2022-04-21T18:00:00
```
This will again execute a single forecast, but this time it will be executed by the service. This now allows us to create a schedule for the forecastseries, which will automatically execute forecasts at the specified times. More information about the schedule settings can be found [here](https://github.com/swiss-seismological-service/hermes/blob/main/docs/concepts.md#forecast-series-scheduling).

```
hermes schedules create fs_induced --config examples/induced/schedule_replay.json
```
This schedule specifies forecasts in the past. Accordingly, no future forecasts will be executed, but the `catchup` command can be used to execute all forecasts as a "replay".
```
hermes schedules catchup fs_induced
```

__Note__ that a schedule can either lie in the past, the future, or both. The `catchup` command will only execute forecasts in the past, while the service will automatically execute forecasts in the future.

## Debugging
To view the forecasts and modelruns, currently only the webservice is available. The available endpoints are listed in the [API documentation](http://localhost:8000/docs).

To view the status of the latest forecasts, you can navigate to the following URL: [http://localhost:8000/v2/forecasts](http://localhost:8000/v2/forecasts).

To more easily debug the models, you can download the exact configuration and input files the modelrun used. You need copy the `oid` of the modelrun you'd like to download and then navigate to the following URL: `http://localhost:8000/v2/modelruns/{oid}/input`

## Results

The results of the modelruns can be directly downloaded from the webservice. This API is still under development and will be improved in the future. The results can be downloaded from the following URL: `http://localhost:8000/v2/modelruns/{oid}/result`. In the future, a more user-friendly interface will be provided.


## Reinstall
If you want to update the project and would like a clean install or/and don't care about the existing data, you can do so by running the following commands:

To update, first go to the `src/hermes` folder and pull the latest changes. Then force-reinstall the dependencies to be sure that the correct versions are installed:

```bash
cd src/hermes
git pull
pip install -e src/hermes --force-reinstall
cd ../..
```

Optionally do the same for the models.  

Update the prefect docker containers:

```bash
docker compose -f src/hermes/compose-prefect.yaml down -v
docker compose -f src/hermes/compose-prefect.yaml pull
docker compose -f src/hermes/compose-prefect.yaml up -d
```

Next you can update the hermes database and webservice:
```bash
docker compose -f src/hermes/compose-database.yaml pull
docker compose -f src/hermes/compose-database.yaml build
docker compose --env-file .env -f src/hermes/compose-database.yaml up -d
```

Now update the database:
```bash
hermes db upgrade
```

## Update
If you want to update the project and would like to keep the existing data, you can do so by running the following commands:

To update, first go to the `src/hermes` folder and pull the latest changes. Then force-reinstall the dependencies to be sure that the correct versions are installed:

```bash
cd src/hermes
git pull
pip install -e src/hermes --force-reinstall
cd ../..
```

Optionally do the same for the models.

Update the prefect docker containers:

```bash
docker compose -f src/hermes/compose-prefect.yaml up -d
prefect server database upgrade -y
```

Next you can update the hermes database and webservice:
```bash
docker compose -f src/hermes/compose-database.yaml up -d --build
hermes db upgrade
```
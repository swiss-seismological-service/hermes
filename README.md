# HERMES - *Hub for Earthquake foRecasts ManagEment and Scheduling*
©2024 ETH Zurich

## Overview
This project is under active development. The goal is to provide an orchestration and scheduling platform for earthquake forecast models. 

For v1 of the project, see the [gitlab repository](https://gitlab.seismo.ethz.ch/indu/rt-ramsis)

## Installation
This installation instruction is merely a recommendation for a user of the software. Depending on your preferences and knowledge, you are free to choose a different setup.


#### 1. Install Docker
Follow the instructions [here](https://docs.docker.com/get-docker/)

#### 2. Create a working directory with a Python virtual environment
Required Python version is 3.12
```
mkdir hermes-project && cd hermes-project
python3 -m venv env
source env/bin/activate
pip install -U pip wheel setuptools
pip install -e .
```

#### 3. Clone the repository into a subfolder
```
git clone https://github.com/swiss-seismological-service/hermes.git src/hermes
```

#### 4. Install the required Python packages
```
pip install -e src/hermes
```

#### 5. Configure environment file
```
cp src/hermes/.env.example .env
```
As a quick test setup, the configuration works as is, but is not secure. Please change the credentials, ports and connection strings in the .env file as well as in the compose files (see below) according to your needs.

#### 6. Start the services
```
docker compose -f src/hermes/compose-prefect.yaml up -d
docker compose -f src/hermes/compose-database.yaml --env-file .env up -d
```
If you want to change the credentials of the prefect database, you can pass along the `POSTGRES_...` and `PREFECT_...` variables to the compose-prefect yaml file. Do not forget to adapt the database connection string in the application .env file.


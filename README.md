# RT-RAMSIS

The focus of this software is now purely as a way to run Seismicity Forecast Models in an operational way. By storing configuration and results in a database, the data is reproducible with recorded origins. Forecasts are scheduled automatically based on user configuration and the status of tasks and model runs is recorded.

RT-RAMSIS is licensed under the [*AGPL* license]
(https://gitlab.seismo.ethz.ch/indu/rt-ramsis/blob/master/LICENSE) to be 
compatible with some of the libraries we use.


## System design and components

### Summary of the RAMSIS workflow

RT-RAMSIS is a controller for time and spatial dependent seismicity. The scheduler works for real-time and back-dated running of forecasts.

As data input, it expects seismic information available in QuakeML from an 
fdsnws/event standard web service. For induced seismicity, borehole data including flow & pressure measurements from a HYDWS web service.

The first thing to configure are the model configs that will be used in the forecasts. There will be a new model config for any time an attribute or key in the config needs to be updated, so the name should be descriptive. The model config contains the following:

* name – This is a unique name for the model configuration.
* Description – further information on the model configuration
* enabled
* sfm_module – This is the module name where the wrapper class is stored on the local machine that it will run on. e.g. ‘ramsis_nsfm.models.etas’
* sfm_class – This is the name of the wrapper class e.g. ‘ETASCalculation’
* tags e.g. [“RISE”, “NATURAL”, “2.0”] which combine with forecastseries tags to choose which models should get run for which forecasts. Only one tag is required on a model and more tags can be added later if desired.


The top level of data is a project. This contains information:

* What data is required (catalog, hydraulic data, injection plan data)\
* urls of any data sources if these should be retrieved every forecast (if data if often retrospectively altered, this will always use the most up to date data)
* Data (If we want the same data for every forecast. This reduces wait-times as data is not fetched every time.)

For each project, forecast series should be defined in order to run forecasts. This contains information on how to run a forecast when it is triggered by the scheduler. The following information is stored here:

* starttime of the forecast series
* endtime of the forecast series
* geometryextent which is the area which the forecast will take place in
* tags e.g. [“RISE”, “NATURAL”, “2.0”] which combine with model tags to choose which models should get run.
* Injectionplans if required.
* Forecastinterval which is the number of seconds between scheduled forecasts.

When the forecast series is scheduled, forecasts will get scheduled from (and including) the starttime, at intervals (defined by forecastinterval) until the endtime (not including this time unless it coincides with the interval)


The spatial area of forecasting is defined by either a Shapely style polygon in  WGS84 coordinates, or a bounding box for any projection that can be defined by a proj string.


## Background Services
There are some services that must be run to enable scheduling with RAMSIS. Prefect is a workflow and orchestration tool that allows scheduling and concurrency of tasks. Once RAMSIS is installed, the following must be set up:

### Prefect Server
```
prefect server start --expose
```
The --expose option means that the port that the server is running on is exposed so that it can be accessed remotely.

### Prefect Agent
```
prefect agent start "default" --api http://127.0.0.1:4200/api
```
Both of the prefect services can be started in seperate windows for testing, or with a background service tool such as systemd which will ensure a more operational setup.

A PostgreSQL database is required, and instructions for installation can be found below.

### Input of seismic data
Seismic data is expected to be provided in QuakeML format from an FDSN/event web 
service, specified at http://www.fdsn.org/webservices/fdsnws-event-1.2.pdf .
The typical way to provide this service may be to populate a SeisComP3 
compatible database and run the SeisComP3 fdsnws module on top of it: 
https://docs.gempa.de/seiscomp3/current/apps/fdsnws.html

The location and boundary parameters of the FDSN/event web service are a RAMSIS
project configuration

### Input of hydraulic data data
Hydraulic data is expected in json format from a HYDWS web service. SED provides
HYDWS as a ready-to-use freeware software package at 
https://gitlab.seismo.ethz.ch/sed-infra/hydws , alongside with documentation. 
HYDWS uses (and installs) a postgres database for hydraulic data. Auxiliary 
Software to insert hydraulic data from project-specific measurement gear into
the database needs to be implemented specifically for each service setup.

Note: HYDWS supports multiple boreholes, borehole sections, and measurement
parameters. Individual seismicity models may need, or support only a subset of 
of those. It is checked at runtime whether a seismicity model can handle the
hydraulic data it is provided with, and whether it is sufficient to parametrize
the model.

The location and boundary parameters of the HYDWS web service are a RAMSIS
project configuration

### The RT-RAMSIS core

This repository contains the task management and work flow functionality. Serialization/deserialization and the SQLalchemy datamodel is stored in the ramsis.datamodel repository, Helper functions that may be used by both RAMSIS and the model wrapper, such as spatial transformation functions, are stored in ramsis.utils.



RAMSIS has two options for input data:
* Via web services, FDSN or HYD web services. This is important for real time running of RAMSIS. This means that the data will always be fetched at run time and therefore be up to date. The urls of these web services will be defined at the project level but the input data will be stored with each forecast.
* Via predefined data that is stored on the Project. In this case, the same input data will be used for every forecast.

All web service components can be assessed remotely, over inthernet, and thus
can be maintained by other responsibles, in different environments, operating
systems, etc. Multiple RT-RAMSIS instances may use overlapping sets of web 
services.

Requirements and installation is described below.

### The data model and tools.
In order to make the data abstraction available as a dependency to seismicity 
forecast models and future analysis software, the data model, along with 
serialization/deserialization capability to a PostgreSQL database is provided
as a standalone package here: 
https://gitlab.seismo.ethz.ch/indu/ramsis.datamodel.
Also other functionality useful to both RT-RAMSIS core and seismicity forecast
model workers are packaged as "utilities" 
here: https://gitlab.seismo.ethz.ch/indu/ramsis.utils

### The seismicity forecast models
Seismicity forecast models receive past seismicity catalogs and (in case of 
induced seismicity) hydraulic history, and hydraulic plans, over a web service 
interface. To foster the integration of seismicity forecast models, the web 
service interface of seismicity forecast model is offered as an independent
package: https://gitlab.seismo.ethz.ch/indu/ramsis.sfm.worker ("seismicity 
forecast model worker"). It implements the web service interface and job 
handling. 


Models available with the newest version of RAMSIS are:
* ETAS: https://gitlab.seismo.ethz.ch/indu/ramsis-nsfm (wrapper for natural seismicity models)
https://github.com/swiss-seismological-service/etas (model code called by wrapper)

* EM1 will shortly be updated to work with the latest version: https://gitlab.seismo.ethz.ch/indu/ramsis-sfm


Seismicity forecast models are typically provided by scientists, have 
dependencies on many software packages and OSs, and variable incocation 
interfaces. An overview of the models identified and tentatively planned for
integration is at https://wiki.seismo.ethz.ch/doku.php?id=pro:sc_proj:coseismiq
. Further models (for time-dependent non-induced risk) shall be nominated by 
the RISE project.

So, in order to get a model operational, you need an adapter between the web 
service provider and the model. This translates the data between that stored by ramsis.datamodel and what is required by the model itself.

A web service is required to be setup to run these models through RAMSIS. This web service ensures that a model can be run on a remote machine and that results are saved to a local database on the model side. 

To find information about setting up a model worker, plese follow this link:

https://gitlab.seismo.ethz.ch/indu/ramsis.sfm.worker



### Installation of the RT-RAMSIS core
Create a virtual or conda environment to install dependencies into. The following instructions are for conda on a linux machine


Install conda:
```
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
chmod +x Miniconda3-latest-Linux-x86_64.sh
./Miniconda3-latest-Linux-x86_64.sh
```
Create a conda environment
```
conda create -n ramsis python=3.8
conda activate ramsis
```

Set up a Postgresql database

If you don't have postgresql already on your system, it is recommended to
install a docker container containing everything needed for convenience.


### Install Docker and other dependencies
```
sudo apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io
```

### Create Docker postgres container
Configure with whatever parameters are correct for the situation
Note: This will create a postgres instance with a username=postgres, port=5432
If 5432 is already used, please alter the entry as follows: -p 5433:5432 where
5433 is the port on your local machine used. The second port must be 5432 as
this is the automatically configured port used inside the docker container for postgresql.
```
docker pull postgres
mkdir -p $HOME/docker/volumes/postgres
docker run  --name ramsis -e POSTGRES_PASSWORD=ramsis -d -p 5432:5432 -v $HOME/docker/volumes/postgres:/var/lib/postgresql/data --restart unless-stopped postgres
```

Check that the docker image is running
```
docker ps
# Should show the runnng container
```

Log into postgres instance and create ‘ramsis’ database
Note: If you have changed the port used for the docker container, you will need
to alter it here.
```
psql -p 5432 -h localhost -U postgres
create database ramsis;
\q
```


# Configure environment

A .env file will be needed with the postgres credentials:
```
POSTGRES_USER=postgres
POSTGRES_PASSWORD=ramsis_password
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=ramsis
```

And if running testing is wanted, a .env.test should be setup as follows:
```
DEFAULT_USER=postgres
DEFAULT_DB=ramsis
DEFAULT_PASSWORD=ramsis_password
POSTGRES_PORT=5432
POSTGRES_SERVER=localhost
POSTGRES_USER=test
POSTGRES_PASSWORD=test
POSTGRES_DB=ramsis_test
```

Where a test user and test database will be setup which will not interfere with the operational database. The ‘DEFAULT’ credentials should be the same as those in the .env file while the ‘POSTGRES’ credentials should be the test ones. You do not need to setup a test user or database as this will be done automatically with the information provided in the .env.test file. With testing run ‘$ pytest’ from the RAMSIS directory.


Create directory
```
$ export PATH_PROJECTS=$HOME/work/projects
$ mkdir -pv $PATH_PROJECTS
```


Clone the datamodel dependency and install
```
$ cd $PATH_PROJECTS
$ git clone https://gitlab.seismo.ethz.ch/indu/ramsis.datamodel.git
$ cd ramsis.datamodel
$ git checkout main
$ pip install -e .
```

Clone the ramsis.utils repository

```
git clone https://gitlab.seismo.ethz.ch/indu/ramsis.utils.git
git checkout main
pip install .
```


Clone the repository and install RAMSIS

```
$ cd $PATH_PROJECTS
$ git clone https://gitlab.seismo.ethz.ch/indu/RAMSIS.git
$ cd rt-ramsis
$ git checkout main
$ cd $PATH_PROJECTS/RAMSIS
$ pip install .
```


# Setup of RAMSIS

## Create configuration files
 Please see the following examples of configuration files as a guide to create and modify for different needs at RAMSIS/tests/resources:
model_etas.json (Configured for etas model)
model_seis.json (configured for bedretto data)
project_etas.json
forecast_series.json

(TODO add further description of all the configuration parameters)


## Load configuration to RAMSIS database:
```
ramsis model load [OPTIONS]                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         
 Options:
*  --model-config        PATH  Path to model config containing Seismicity Model config [default: None] [required]                                                                                                                                          

```
e.g.
         
ramsis model load --model-config RAMSIS/tests/resources/model_etas.json



```
ramsis project create [OPTIONS]
 Options:
*  --config        PATH  Path to json project config. [default: None] [required]

```
e.g. 
ramsis project create --config RAMSIS/tests/resources/project_etas.json



```
ramsis forecastseries create [OPTIONS]
 Options:
*  --config            PATH     [default: None] [required]                                                                                                                                                                                                         	--project-id        INTEGER  Project id to associate the forecast series to. If not provided, the latest project id will be used. [default: None]  

```
e.g
ramsis forecastseries create --config RAMSIS/tests/resources/forecast_etas.json


Once at least one model, project and forecast series are setup, and you have a model worker web service running, it is possible to run a forecast.


Running RAMSIS

```
ramsis forecastseries schedule [OPTIONS] FORECASTSERIES_ID
 Options:
 *    forecastseries_id      INTEGER  [default: None] [required
```
e.g. ramsis forecastseries schedule 1


This will start a forecastseries according to the schedule defined in the forecastseries config.




## Developers and Contributors

Please read the [Contribution
guide](https://gitlab.seismo.ethz.ch/indu/rt-ramsis/blob/master/CONTRIBUTING.md)
before you add code to the project. The contribution guide also contains infos
on how you can access the code documentation.

## Copyright
Copyright (c) 2015-2018, Swiss Seismological Service, ETH Zurich and
Geo-Energie Suisse AG, Zurich

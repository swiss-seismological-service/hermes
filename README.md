# RT-RAMSIS

Real Time Risk Assessment and Mitigation for Induced Seismicity.

RT-RAMSIS is a KTI project that is developed in collaboration with Geo-Energie
Suisse AG. It is the successor of ATLS, a prototype software developed under
GEOSIM.

**NOTE: Geo-Energie Suisse AG and SED have agreed not to actively distribute
RT-RAMSIS to third parties. It is internal use only. If you're an employee of
either company you must not distribute the code to anyone without prior 
permission of GES or SED.** 

RT-RAMSIS is licensed under the [*AGPL* license]
(https://gitlab.seismo.ethz.ch/indu/rt-ramsis/blob/master/LICENSE) to be 
compatible with some of the libraries we use.


## System design and components

### Summary of the RAMSIS workflow

RT-RAMSIS is a controller for real-time (or playback) time dependent seismicity,
seismic hazard, and risk assessment. 

As data input, it expects seismic information available in QuakeML from an 
fdsnws/event standard web service, and (for induced seismicity), borehole, and 
borehole operation (flow & pressure measurements) from a HYDWS web service.

Internally, it is organized in projects.
For each project, a series of scenarios can be defined. A scenario is defined, 
*  in its seismicity stage, it is defined by a series of forecast models with 
respective configuration, and "injection plan" (planned future hydraulic data)
* in its hazard stage, by an Openquake logic tree model containing the 
seismicity models as branches, and providing the possibility to weight them
* in its risk stage, [...pending]

Scenarios have execution times, and timespans for which a/b values (seismicity 
stages), hazard curves and maps (hazard), and (risk) are calculated. 

Each seismicity model of a scenario is configured for a volume, or a set of 
subvolumes, for which it is executed.

All these configurations and settings are done in a QT-based GUI local to the 
machine running the RAMSIS core.

RAMSIS constantly checks the available configuration, and if current (or 
modelled) time matches a scenario execution time, it
1.  Invokes all due seismicity models via a web service interface, providing 
them with model configuration, definition of the target volumes, full seismic
and hydraulic history, and injection plan
2. the models return a and b values for each volume and requested time interval.
3. RAMSIS uses these results to parametrize the source models of an OpenQuake
hazard calculation, and invokes this using the OpenQuake web service API
4. After completion of the hazard calculations, RAMSIS fetches the results
and stores hazard maps & curves to a database
5. [risk computation, pending]
6. [threshold analysis and alarming, pending]

All calculation configurations, as well as calculation results are (will be) 
browsable in a web-based read-only GUI, based on OpenCMS & SED Flexitable 
technology.


![RAMSIS block model](RT-RAMSIS-geothermica.png "RAMSIS block model")


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

Note: HYDWS supports multiple boreholes, borehole sections, and meadurement
parameters. Individual seismicity models may need, or support only a subset of 
of those. It is checked at runtime whether a seismicity model can handle the
hydraulic data it is provided with, and whether it is sufficient to parametrize
the model

The location and boundary parameters of the HYDWS web service are a RAMSIS
project configuration

### The RT-RAMSIS core

... (i.e. this repository) comprises the functionality of the QT config GUI, the
task managers, serialization/deserialization, and the clients to all web 
services (fdsnws/event, hydws, seismicity forecast models, openQuake hazard
assessment, risk assessment), and, in future, the thresholding and alerting. 
Requirements and nstallation is described below. The core depends on the data 
model, and, in order to provide real functionality, on the web services.
All web service components can be assessed remotely, over inthernet, and thus
can be maintained by other responsibles, in different environments, operating
systems, etc. Multiple RT-RAMSIS instances may use overlapping sets of web 
services.

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


Models available are:
* HM1: https://gitlab.seismo.ethz.ch/indu/hm1_model
* EM1: https://gitlab.seismo.ethz.ch/indu/ramsis.sfm.em1

Seismicity forecast models are typically provided by scientists, have 
dependencies on many software packages and OSs, and variable incocation 
interfaces. An overview of the models identified and tentatively planned for
integration is at https://wiki.seismo.ethz.ch/doku.php?id=pro:sc_proj:coseismiq
. Further models (for time-dependent non-induced risk) shall be nominated by 
the RISE project.

So, in order to get a model operational, you need an adapter between the web 
service provider and the model.
* in case of HM1, this adapter is 
https://gitlab.seismo.ethz.ch/indu/ramsis.sfm.hm1 (work in progress)
* (in case of EM1, which is fully operational, the model was re-implemented
within the customization of the adapter in 
https://gitlab.seismo.ethz.ch/indu/ramsis.sfm.em1)

### Hazard calculator
RT-RAMSIS uses OpenQuake as hazard calculation, (available from here:
https://github.com/gem/oq-engine/) , which involves a REST server API: 
https://github.com/gem/oq-engine/blob/master/doc/web-api.md . RT-RAMSIS core 
just needs to be configured with the URL of the OpenQuake installation. The list
of GMPE models available for hazard calculation is given by those available
in openquake 
(see https://github.com/gem/oq-engine/tree/master/openquake/hazardlib/gsim), and
referenced in the logic tree template file of the project.

### The WEB GUI
The Web GUI is planned as an OpenCMS/Flexitable application directly accessing
RT-RAMSIS's database directly in read-only mode. The WEB GUI will be prepared 
as a virtual machine, however it is not ready yet.


# Installation of the RT-RAMSIS core (for developers)

GDAL is required. This can be tricky to install so it is recommended to install
miniconda, and then use a conda environment to install dependencies into.

This can be done on the command line on a linux machine:
```
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
chmod +x Miniconda3-latest-Linux-x86_64.sh
./Miniconda3-latest-Linux-x86_64.sh
conda create -n ramsis python=3.6
conda activate ramsis
```

Make sure the dependencies

* git
* graphviz
* libxml2-dev
* libxslt1-dev
* zlib1g-dev
* GDAL

are installed on your system.


```
sudo apt-get update -y
sudo apt install graphviz
sudo apt-get install libxml2-dev
sudo apt-get install -y libxslt1-dev
sudo apt-get install -y zlib1g-dev
conda install -c conda-forge gdal
```

Set up a Postgresql database

If you don't have postgresql already on your system, it is recommended to
install a docker container containing everything needed for convenience.

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

Create Docker postgres container
Configure with whatever parameters are correct for the situation
```
docker pull postgres:11
mkdir -p $HOME/docker/volumes/postgres
docker run --rm   --name ramsis -e POSTGRES_PASSWORD=ramsis -d -p 5432:5432 \
    -v $HOME/docker/volumes/postgres:/var/lib/postgresql/data  postgres:11
```
Check that the docker image is running
```
docker ps
# Should show the runnng container
```

Clone the repository

```
$ export PATH_PROJECTS=$HOME/work/projects
$ mkdir -pv $PATH_PROJECTS
$ git clone https://gitlab.seismo.ethz.ch/indu/RAMSIS.git $PATH_PROJECTS/RAMSIS
$ git checkout develop
```

Finally install RAMSIS

```bash
$ cd $PATH_PROJECTS/RAMSIS
$ pip install -e .
```

Test your installation with

```bash
$ ramsis -h
```
**NOTE:** In the description above the variables `PATH_PROJECTS` and
`PATH_THIRD` are used. Adjust the corresponding values according to your needs.

Set up the RAMSIS config
* Open $PATH_PROJECTS/config/ramsis_config.yml
* update name of the db (any name), port (same as setup in docker), password (same as setup for docker), user (postgres user as setup for docker)

Initialize database
start RAMSIS
`ramsis`
On RAMSIS open application settings from file
Press 'Init DB'

Close ramsis
Install any project data that might be required, or set up first project.


## Developers and Contributors

Please read the [Contribution
guide](https://gitlab.seismo.ethz.ch/indu/rt-ramsis/blob/master/CONTRIBUTING.md)
before you add code to the project. The contribution guide also contains infos
on how you can access the code documentation.

## Copyright
Copyright (c) 2015-2018, Swiss Seismological Service, ETH Zurich and
Geo-Energie Suisse AG, Zurich

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

RT-RAMSIS is a controller for real-time (or playback) time dependent seismicity,
seismic hazard, and risk assessment. 

As data input, it expects seismic information available in QuakeML from an 
fdsnws/event standard web service, and (for induced seismicity), borehole, and 
borehole operation (flow & pressure measurements) from a HYDWS web service.
Internally, it is organized in projects.



## Installation (for developers)

Make sure the dependencies

* git
* graphviz
* libxml2-dev
* libxslt1-dev
* python3.6
* python3-pip
* python-virtualenv
* zlib1g-dev

are installed on your system.

Clone the repository

```bash
$ export PATH_PROJECTS=$HOME/work/projects
$ mkdir -pv $PATH_PROJECTS
$ git clone https://gitlab.seismo.ethz.ch/indu/RAMSIS.git $PATH_PROJECTS/RAMSIS
```

Set up a virtual environment

```bash
$ virtualenv -p $(which python3.6) $PATH_PROJECTS/RAMSIS/venv3
$ source $PATH_PROJECTS/RAMSIS/venv3/bin/activate
```

Install [OpenQuake](https://github.com/gem/oq-engine)

```bash
$ export PATH_THIRD=$HOME/work/3rd
$ mkdir -pv $PATH_THIRD
$ git clone https://github.com/gem/oq-engine.git $PATH_THIRD/oq-engine
$ pip install -r $PATH_THIRD/oq-engine/requirements-py36-linux64.txt
$ pip install -e $PATH_THIRD/oq-engine/
```

and install the custom GSIMs

```bash
$ cp -v $PATH_PROJECTS/RAMSIS/RAMSIS/resources/oq/gmpe-gsim/* \
  $PATH_THIRD/oq-engine/openquake/hazardlib/gsim/
```

Start the OpenQuake engine

```bash
$ oq engine --upgrade-db -y
```

Finally install RAMSIS

```bash
$ cd $PATH_PROJECTS/RAMSIS
$ make install
```

Test your installation with

```bash
$ ramsis -h
```
**NOTE:** In the description above the variables `PATH_PROJECTS` and
`PATH_THIRD` are used. Adjust the corresponding values according to your needs.


## Developers and Contributors

Please read the [Contribution
guide](https://gitlab.seismo.ethz.ch/indu/rt-ramsis/blob/master/CONTRIBUTING.md)
before you add code to the project. The contribution guide also contains infos
on how you can access the code documentation.

## Copyright
Copyright (c) 2015-2018, Swiss Seismological Service, ETH Zurich and
Geo-Energie Suisse AG, Zurich

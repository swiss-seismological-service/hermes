#!/usr/bin/env bash

# This bootstrap scripts sets up the dependencies for RAMSIS development
# on an ubuntu trusty (14.04) machine.
#
# Note that while you might use this script to set up your own machine,
# it's original intention was to be used in combination with vagrant,
# i.e. it mostly assumes that the target machine is empty at the time
# the script is executed.

# add OpenQuake repository
add-apt-repository ppa:openquake/ppa
apt-get update

# dependencies for RAMSIS
DEB_PACKAGES="python-qt4 python-qt4-gl qgis python-mock python-sphinx python-sqlalchemy python-pip python-oq-engine git"
PIP_PACKAGES="numpy pymatlab"

# install deb and pip packages
apt-get install -y --force-yes $DEB_PACKAGES
pip install $PIP_PACKAGES

# install pyqtgraph (custom version until this gets merged into the main repo)
git clone https://github.com/3rdcycle/pyqtgraph.git
cd pyqtgraph
git checkout date-axis-item
python setup.py install

# install custom GSIMs
cp /vagrant/ramsis/resources/oq/gmpe-gsim/* /usr/lib/python2.7/dist-packages/openquake/hazardlib/gsim

# upgrade OpenQuake database
oq-engine --upgrade-db -y

# set QGIS prefix path
export QGIS_PREFIX_PATH=/usr

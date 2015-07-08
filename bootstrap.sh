#!/usr/bin/env bash

# This bootstrap scripts sets up the dependencies for ATLS development
# on an ubuntu trusty (14.04) machine.
#
# Note that while you might use this script to set up your own machine,
# it's original intention was to be used in combination with vagrant,
# i.e. it mostly assumes that the target machine is empty at the time
# the script is executed.

# add OpenQuake repository
add-apt-repository ppa:openquake/ppa
apt-get update

# dependencies for ATLS
DEB_PACKAGES="python-qt4 python-qt4-gl qgis python-mock python-sqlalchemy python-pip python-oq-engine"
PIP_PACKAGES="numpy pymatlab"

# install deb and pip packages
apt-get install -y --force-yes $DEB_PACKAGES
pip install $PIP_PACKAGES

# install pyqtgraph 0.9.10-1
wget http://www.pyqtgraph.org/downloads/python-pyqtgraph_0.9.10-1_all.deb
sudo dpkg -i python-pyqtgraph_0.9.10-1_all.deb

# upgrade OpenQuake database
oq-engine --upgrade-db -y

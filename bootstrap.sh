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

# add ObsPy repository and public key
echo "deb http://deb.obspy.org trusty main" >> /etc/apt/sources.list
PUBLIC_KEY=https://raw.github.com/obspy/obspy/master/misc/debian/public.key
wget --quiet -O - $PUBLIC_KEY | sudo apt-key add -

# dependencies for RAMSIS
DEB_PACKAGES="python-qt4 python-qt4-gl qgis python-mock python-obspy"\
" python-sqlalchemy python-pip python-oq-engine python-nose python-lxml git"\
" graphviz"
PIP_PACKAGES="numpy pymatlab sphinx"

# install deb and pip packages
apt-get update
apt-get install -y --force-yes $DEB_PACKAGES
pip install $PIP_PACKAGES

# install pyqtgraph (custom version until this gets merged into the main repo)
git clone https://github.com/3rdcycle/pyqtgraph.git
cd pyqtgraph
git checkout date-axis-item
python setup.py install

# install custom GSIMs
cp /vagrant/atls/resources/oq/gmpe-gsim/* \
/usr/lib/python2.7/dist-packages/openquake/hazardlib/gsim

# upgrade OpenQuake database
oq-engine --upgrade-db -y

# set QGIS prefix path for all users
echo "export QGIS_PREFIX_PATH=/usr" > /etc/profile.d/qgis_prefix.sh

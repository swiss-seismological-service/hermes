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
DEB_PACKAGES=""\
" dvipng=1.14-2"\
" git=1:1.9.1-1ubuntu0.3"\
" graphviz=2.36.0-0ubuntu3.1"\
" python-epydoc=3.0.1+dfsg-4"\
" python-lxml=3.3.3-1ubuntu0.1"\
" python-mock=1.0.1-3"\
" python-nose=1.3.1-2"\
" python-obspy=1.0.1-1~trusty"\
" python-oq-engine=1.9.1-0~trusty01"\
" python-pip=1.5.4-1ubuntu3"\
" python-qt4=4.10.4+dfsg-1ubuntu1"\
" python-qt4-gl=4.10.4+dfsg-1ubuntu1"\
" python-sqlalchemy=0.8.4-1build1"\
" qgis=2.0.1-2build2"\
" texlive-latex-base=2013.20140215-1"
PIP_PACKAGES=""\
" flask==0.11.1"\
" flask-restless==0.17.0"\
" flask-sqlalchemy==2.1"\
" numpy==1.8.2"\
" pymatlab==0.2.3"\
" sphinx==1.4.1"\
" sphinx-rtd-theme==0.1.9"

# install deb and pip packages
apt-get update
for deb_package in $DEB_PACKAGES
do
    apt-get install -y $deb_package
done
for pip_package in $PIP_PACKAGES
do
    pip install $pip_package
done

# install pyqtgraph (custom version until this gets merged into the main repo)
git clone https://github.com/3rdcycle/pyqtgraph.git
cd pyqtgraph
git checkout date-axis-item
python setup.py install

# install custom GSIMs
cp /vagrant/ramsis/resources/oq/gmpe-gsim/* \
/usr/lib/python2.7/dist-packages/openquake/hazardlib/gsim

# upgrade OpenQuake database
oq-engine --upgrade-db -y

# set QGIS prefix path for all users
echo "export QGIS_PREFIX_PATH=/usr" > /etc/profile.d/qgis_prefix.sh

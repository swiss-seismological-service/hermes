#!/usr/bin/env bash
# =============================================================================
# This is <bootstrap.sh>
# =============================================================================
#
# Purpose: This bootstrap scripts sets up the dependencies for RAMSIS
# development on an ubuntu trusty (14.04) machine.
#
# Note that while you might use this script to set up your own machine,
# it's original intention was to be used in combination with vagrant,
# i.e. it mostly assumes that the target machine is empty at the time
# the script is executed.
#
# REVISIONS AND CHANGES
# 2018/01/22  V0.1    (damb): Proceeding
#
# =============================================================================

# dependencies for RAMSIS
DEB_PACKAGES=""\
" dvipng=1.15-0ubuntu1"\
" git=1:2.14.1-1ubuntu4"\
" graphviz=2.38.0-16ubuntu2"\
" libxml2-dev=2.9.4+dfsg1-4ubuntu1.2"\
" libxslt1-dev=1.1.29-2.1ubuntu1"\
" python3"\
" python3-pip"\
" python-virtualenv"\
" texlive-latex-base=2017.20170818-1"\
" zlib1g-dev=1:1.2.11.dfsg-0ubuntu2"

#" python-oq-engine"\
#" python-qt4=4.11.4+dfsg-1build4"\
#" python-qt4-gl=4.11.4+dfsg-1build4"\

PIP_PACKAGES=""\
" epydoc==3.0.1"\
" flask==0.11.1"\
" flask-restful==0.3.5"\
" flask-restless==0.17.0"\
" flask-sqlalchemy==2.1"\
" lxml==3.3.3"\
" marshmallow==2.10.3"\
" matplotlib"\
" nose==1.3.1"\
" numpy==1.8.2"\
" obspy==1.0.2"\
" PyOpenGL==3.1.1a1"\
" PyQt5==5.9.2"\
" pymap3d"\
" pymatlab==0.2.3"\
" sphinx==1.4.1"\
" sphinx-rtd-theme==0.1.9"\
" sqlalchemy==0.8.4"

PATH_PYTHON3=$(which python3)
PATH_RAMSIS=$(pwd)

RAMSIS_OWNER=$(stat -c "%U" "${PATH_RAMSIS}")
RAMSIS_GROUP=$(stat -c "%G" "${PATH_RAMSIS}")
HOME_RAMSIS_OWNER=$( getent passwd "$RAMSIS_OWNER" | cut -d: -f6 )

PATH_OPENQUAKE_INSTALL="$HOME_RAMSIS_OWNER/work/3rd/oq-engine"

# -----------------------------------------------------------------------------
print_msg() {
  # utility function to print a message
  echo -ne "($(basename $0)) $1\n"
}

warn() {
  print_msg "WARNING: $1"
}

error() {
  print_msg "ERROR: $1"
  exit 2
}

# -----------------------------------------------------------------------------
# install deb packages
apt-get update
for deb_package in $DEB_PACKAGES
do
    apt-get install -y $deb_package || \
      error "Installation of '$deb_package' failed (apt-get)."
done

# create virtualenv
virtualenv -p "$PATH_PYTHON3" "${PATH_RAMSIS}/venv3"

VENV_PIP="${PATH_RAMSIS}/venv3/bin/pip"

for pip_package in $PIP_PACKAGES
do
  "$VENV_PIP" install $pip_package || \
    error "Installation of '$pip_package' failed (pip)."
done

# install OpenQuake from sources (development version)
mkdir -pv "$PATH_OPENQUAKE_INSTALL"
test ! -d "$PATH_OPENQUAKE_INSTALL" && \
  git clone https://github.com/gem/oq-engine.git \
  "$PATH_OPENQUAKE_INSTALL" || \
  warn "$PATH_OPENQUAKE_INSTALL already existing."

PY_VERSION=$("${PATH_RAMSIS}/venv3/bin/python" --version | \
  cut -d ' ' -f2 | cut -d '.' -f 1,2)

"$VENV_PIP" install -r \
  "$PATH_OPENQUAKE_INSTALL/requirements-py${PY_VERSION/./}-linux64.txt"
"$VENV_PIP" install -e "${PATH_OPENQUAKE_INSTALL}"

# install custom GSIMs to OpenQuake
cp -v "${PATH_RAMSIS}"/ramsis/ramsis/resources/oq/gmpe-gsim/* \
  "${PATH_OPENQUAKE_INSTALL}"/openquake/hazardlib/gsim

# install pyqtgraph (custom version until this gets merged into the main repo)
${PATH_RAMSIS}/venv3/bin/pip install \
  git+https://github.com/3rdcycle/pyqtgraph.git@date-axis-item

chown -R ${RAMSIS_OWNER}:${RAMSIS_GROUP} ${PATH_RAMSIS}/venv3

# upgrade OpenQuake database
${PATH_RAMSIS}/venv3/bin/oq engine --upgrade-db -y

# ---- END OF <bootstrap.sh> ----

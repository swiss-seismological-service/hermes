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
VENV_PY3="${PATH_RAMSIS}/venv3/bin/python3"

# install OpenQuake from sources (development version)
mkdir -pv "$PATH_OPENQUAKE_INSTALL"
([ ! -d "$PATH_OPENQUAKE_INSTALL" ] || \
  [ ! "$(ls -A $PATH_OPENQUAKE_INSTALL)" ]) && \
  git clone https://github.com/gem/oq-engine.git \
  "$PATH_OPENQUAKE_INSTALL" || \
  warn "$PATH_OPENQUAKE_INSTALL already existing."

PY_VERSION=$("$VENV_PY3" --version | \
  cut -d ' ' -f2 | cut -d '.' -f 1,2)

"$VENV_PIP" install -r \
  "$PATH_OPENQUAKE_INSTALL/requirements-py${PY_VERSION/./}-linux64.txt"
"$VENV_PIP" install -e "${PATH_OPENQUAKE_INSTALL}"

# XXX(damb): PyQt5 must be installed by means of pip since only wheel
# distributions are available. See:
# https://mail.python.org/pipermail/distutils-sig/2017-March/030228.html
"$VENV_PIP" install "PyQt5==5.10"


# install RT-RAMSIS
make install VENV="${PATH_RAMSIS}/venv3" || error "Installation failed (make)."

# install custom GSIMs to OpenQuake
cp -v "${PATH_RAMSIS}"/ramsis/ramsis/resources/oq/gmpe-gsim/* \
  "${PATH_OPENQUAKE_INSTALL}"/openquake/hazardlib/gsim

chown -R ${RAMSIS_OWNER}:${RAMSIS_GROUP} ${PATH_RAMSIS}/venv3

# upgrade OpenQuake database
${PATH_RAMSIS}/venv3/bin/oq engine --upgrade-db -y

# ---- END OF <bootstrap.sh> ----

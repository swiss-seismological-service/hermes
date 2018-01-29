# -*- encoding: utf-8 -*-
# This is <setup.py>
# ----------------------------------------------------------------------------
#
# Copyright (c) 2018 by Swiss Seismological Service (SED, ETHZ)
#
# setup.py
#
# REVISIONS and CHANGES
#    2018/01/24   V1.0   Daniel Armbruster (damb)
#
# ============================================================================
"""
setup.py for RT-RAMSIS

.. note:

    Packaging is performed by means of `Python namespace packages
    <https://packaging.python.org/guides/packaging-namespace-packages/>`_
"""

import sys
from setuptools import setup, find_packages


if sys.version_info[:2] < (3, 6):
    raise RuntimeError("Python version >= 3.6 required.")

_name = 'ramsis_rt'

_authors = [
    'Lukas Heiniger',
    'Walsh Alexander',
    'Daniel Armbruster']
_authors_email = [
    'lukas.heiniger@sed.ethz.ch',
    'daniel.armbruster@sed.ethz.ch']

_extras_require = {'doc': [
    "epydoc==3.0.1",
    "sphinx==1.4.1",
    "sphinx-rtd-theme==0.1.9", ]}
_install_requires_app = [
    # XXX(damb): astropy dependency added due to AttributeError
    # AttributeError: module 'scipy.special' has no attribute 'loggamma'
    # while installing pymap3d
    "astropy==2.0.3",
    "lxml==3.3.3",
    "marshmallow==2.10.3",
    "matplotlib",
    # TODO (damb): check if valid version: "numpy==1.8.2",
    "numpy>=1.8.2",
    "obspy==1.0.2",
    "PyOpenGL==3.1.1a1",
    # XXX: Must be installed by means of pip; see:
    # https://mail.python.org/pipermail/distutils-sig/2017-March/030228.html
    "PyQt5 >=5.8.2, <=5.10",
    "pymap3d",
    "pymatlab==0.2.3",
    "pyqtgraph==0.10.0",
    "sqlalchemy==0.8.4", ]
_install_requires_workers = [
    "flask==0.11.1",
    "flask-restful==0.3.5",
    "flask-restless==0.17.0",
    "flask-sqlalchemy==2.1",
    "marshmallow==2.10.3",
    # TODO (damb): check if valid version: "numpy==1.8.2",
    "numpy>=1.8.2",
    # TODO(damb): check PyQt5 deps
    # ramsis/ramsisdata/eqstats.py:from PyQt5 import QtCore
    # ramsis/workers/shapiro/model/common.py:from PyQt5 import QtCore
    # ramsis/workers/etas/model/common.py:from PyQt5 import QtCore
    # ramsis/workers/rj/model.py:from PyQt5 import QtCore
    # XXX: Must be installed by means of pip; see:
    # https://mail.python.org/pipermail/distutils-sig/2017-March/030228.html
    "PyQt5 >=5.8.2, <=5.10",
    "pymatlab==0.2.3",
    "sqlalchemy==0.8.4", ]
_install_requires = _install_requires_app
_install_requires.extend(_install_requires_workers)
_tests_require = ["nose==1.3.1", ]

_include = ('*', )

_entry_points_app = {
    'console_scripts': ['ramsis = ramsis.app.main:main [doc]', ]}
# TODO(damb): entry_points_workers missing yet
_entry_points_workers = {}
_entry_points = {**_entry_points_app, **_entry_points_workers}

_dependency_links_app = [(
    "git+https://gitlab.seismo.ethz.ch/indu/pyqtgraph.git"
    "@d58e7580762767b9ed49421f62ba674e01ca380c#egg=pyqtgraph-0.10.0"), ]
_dependency_links_workers = []
_dependency_links = _dependency_links_app
_dependency_links.extend(_dependency_links_workers)


subsys = sys.argv[1]
if 'ramsis_app' == subsys:
    sys.argv.pop(1)

    _name = 'ramsis_app'
    _install_requires = _install_requires_app
    _include = ('*.app', 'app.*', '*.app.*', 'ramsisdata')
    _entry_points = _entry_points_app
    _dependency_links = _dependency_links_app

elif 'ramsis_workers' == subsys:
    sys.argv.pop(1)
    _name = 'ramsis_workers'
    _install_requires = _install_requires_workers
    _include = ('*.workers', 'workers.*', '*.workers.*', 'ramsisdata')
    _entry_points = _entry_points_workers
    _dependency_links = _dependency_links_workers


setup(
    name=_name,
    # TODO(damb): Provide version string globally
    version='0.1',
    author=' (SED, ETHZ),'.join(_authors),
    author_email=', '.join(_authors_email),
    description=('Real Time Risk Assessment and Mitigation for Induced'
                 'Seismicity'),
    license='AGPL',
    keywords=[
        'induced seismicity',
        'risk',
        'risk assessment',
        'risk mitigation',
        'realtime',
        'seismology'],
    url='https://gitlab.seismo.ethz.ch/indu/rt-ramsis.git',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Console',
        'Environment :: X11 Applications :: Qt',
        'Intended Audience :: Science/Research',
        ('License :: OSI Approved :: GNU Affero '
            'General Public License v3 or later (AGPLv3+)'),
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: Implementation :: CPython',
        'Topic :: Scientific/Engineering', ],
    platforms=['Linux', ],
    # TODO(damb): exclude tests
    packages=['ramsis.' + pkg for pkg in find_packages(
        where='ramsis', include=_include)],
    install_requires=_install_requires,
    extras_require=_extras_require,
    tests_require=_tests_require,
    include_package_data=True,
    zip_safe=False,
    # TODO(damb): test_suite=unittest.TestCase
    # TODO(damb): ramsis does not necessarily depend on doc extras flag
    entry_points=_entry_points,
    dependency_links=_dependency_links
)

# ----- END OF setup.py -----

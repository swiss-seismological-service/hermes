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
setup.py for RAMSIS
"""

import sys
from setuptools import setup, find_packages


if sys.version_info[:2] < (3, 6):
    raise RuntimeError("Python version >= 3.6 required.")

_authors = [
    'Lukas Heiniger',
    'Walsh Alexander',
    'Daniel Armbruster']
_authors_email = [
    'lukas.heiniger@sed.ethz.ch',
    'daniel.armbruster@sed.ethz.ch']

_install_requires = [
    # XXX(damb): astropy dependency added due to AttributeError
    # AttributeError: module 'scipy.special' has no attribute 'loggamma'
    # while installing pymap3d
    "astropy>=2.0.3",
    "GDAL",
    "lxml>=3.3.3",
    "matplotlib",
    "marshmallow==3.0.0rc8",
    # TODO (damb): check if valid version: "numpy==1.8.2",
    "numpy>=1.8.2",
    "obspy==1.1.0",
    "PyOpenGL>=3.1.1a1",
    "PyQt5 >=5.12, <5.13",
    "pymap3d",
    "pyqtgraph==0.10.0",
    "python-dateutil>=2.8.0",
    "PyYAML>=5.1.1",
    "ramsis.datamodel==0.3rc0",
    "requests>=2.18.4",
    "transitions==0.6.9",
    "prefect[viz]",
    "pyproj==2.3.0",
    "pyproj==2.3.0",
    "jinja2",
    "xmltodict",
    "sqlalchemy==1.3.13"]

_extras_require = {'doc': [
    "epydoc==3.0.1",
    "sphinx==1.4.1",
    "sphinx-rtd-theme==0.1.9", ]}

_dependency_links = [(
    "git+https://gitlab.seismo.ethz.ch/indu/pyqtgraph.git"
    "@d58e7580762767b9ed49421f62ba674e01ca380c#egg=pyqtgraph-0.10.0"), (
    "git+https://gitlab.seismo.ethz.ch/indu/ramsis.datamodel.git"
    "#egg=ramsis.datamodel-0.1"), ]

_scripts = []

# TODO(damb): add doc
# TODO LH: find a good way to handle the settings file. The app looks for
#   it in standard config locations defined by QAppConfigLocation which
#   are not writable by setup.py AFAIK.
_data_files = [
    ('', ['LICENSE',
          'Makefile']),
    ('config', ['settings.template.yml']), ]

setup(
    name='RAMSIS',
    # TODO(damb): Provide version string globally
    version='0.1',
    author=' (SED, ETHZ),'.join(_authors),
    author_email=', '.join(_authors_email),
    description=('Real Time Risk Assessment and Mitigation for Induced'
                 'Seismicity. '),
    license='AGPL',
    keywords=[
        'induced seismicity',
        'risk',
        'risk assessment',
        'risk mitigation',
        'realtime',
        'seismology'],
    url='https://gitlab.seismo.ethz.ch/indu/RAMSIS.git',
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
    dependency_links=_dependency_links,
    install_requires=_install_requires,
    extras_require=_extras_require,
    packages=find_packages(),
    data_files=_data_files,
    scripts=_scripts,
    include_package_data=True,
    zip_safe=False,
    # TODO(damb): test_suite=unittest.TestCase
    # TODO(damb): ramsis does not necessarily depend on doc extras flag
    entry_points={
        'console_scripts': ['ramsis = RAMSIS.main:main',
                            'ramsis-sfm-client = RAMSIS.app.client:main', ]}
)

# ----- END OF setup.py -----

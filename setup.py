# -*- encoding: utf-8 -*-
# This is <setup.py>
# ----------------------------------------------------------------------------
#
# Copyright (c) 2018 by Swiss Seismological Service (SED, ETHZ)
#
# setup.py
#
# ============================================================================
"""
setup.py for RAMSIS
"""

import sys
from setuptools import setup, find_packages


if sys.version_info[:2] < (3, 8):
    raise RuntimeError("Python version >= 3.8 required.")

_authors = [
    'Lukas Heiniger',
    'Laura Sarson',
    'Daniel Armbruster']
_authors_email = [
    'lukas.heiniger@sed.ethz.ch',
    'laura.sarson@sed.ethz.ch']

_install_requires = [
    "marshmallow",
    "python-dateutil>=2.8.0",
    "PyYAML>=5.1.1",
    "ramsis.datamodel==1.1",
    "requests>=2.18.4",
    "transitions==0.6.9",
    "prefect==2.10.9",
    "pyproj>=3.2.1",
    "jinja2",
    "sqlalchemy>=1.4",
    "typer",
    "pytest-mock",
    "pytest-order",
    "python-dotenv",
    "psycopg2-binary",
    "pydantic==1.10.11", ]

_extras_require = {'doc': [
    "epydoc==3.0.1",
    "sphinx==1.4.1",
    "sphinx-rtd-theme==0.1.9", ]}

_dependency_links = [(
    "git+https://gitlab.seismo.ethz.ch/indu/ramsis.datamodel.git"
    "#egg=ramsis.datamodel-0.1"), ]

_scripts = []

_data_files = [
    ('', ['LICENSE',
          'Makefile']),
    ('config', ['settings.template.yml']), ]

setup(
    name='RAMSIS',
    version='1.1',
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
        'Programming Language :: Python :: 3.8',
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
    entry_points={
        'console_scripts': ['ramsis = RAMSIS.cli:main', ]}
)

# ----- END OF setup.py -----

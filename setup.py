#!/usr/bin/env python

from __future__ import print_function

import sys

from setuptools import setup
from spoppy import get_version

if sys.version_info < (3, 3):
    print('You need at least python 3.3')
    sys.exit(1)


with open('requirements.txt') as f:
    required = f.read().splitlines()

setup(
    name='Spoppy',
    version=get_version(),
    description='A lightweight spotify CLI',
    author='Sindri Guðmundsson',
    author_email='sindrigudmundsson@gmail.com',
    url='https://irdn.is/',
    packages=['spoppy'],
    test_suite='nose.collector',
    install_requires=required,
    include_package_data=True,
    scripts=[
        'scripts/spoppy'
    ]
)

#!/usr/bin/env python

from __future__ import print_function

import sys

from setuptools import setup
from spoppy import get_version

if sys.version_info < (3, 3):
    print('You need at least python 3.3')
    sys.exit(1)


with open('requirements.txt', 'r') as f:
    required = f.read().splitlines()

with open('README.rst', 'r') as f:
    long_description = f.read()

setup(
    name='spoppy',
    version=get_version(),
    description='A lightweight spotify CLI',
    long_description=long_description,
    author='Sindri Guðmundsson',
    author_email='sindrigudmundsson@gmail.com',
    url='https://github.com/sindrig/spoppy',
    licence='MIT',
    classifiers=[
        'Environment :: Console',
        'Intended Audience :: End Users/Desktop',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: POSIX :: Linux',
        'Operating System :: Unix',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Topic :: Multimedia :: Sound/Audio'
    ],
    keywords='spoppy spotify cli',
    packages=['spoppy'],
    test_suite='nose.collector',
    install_requires=required,
    include_package_data=True,
    zip_safe=False,
    scripts=[
        'scripts/spoppy'
    ]
)

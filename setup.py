#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function

import sys

from setuptools import setup
from spoppy import get_version

if (3, 0) < sys.version_info < (3, 3) or sys.version_info < (2, 7):
    print('You need python 2.7+ or python 3.3+')
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
    author=u'Sindri Guðmundsson',
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
        'Programming Language :: Python :: 2.7',
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

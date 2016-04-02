#!/usr/bin/env python

from setuptools import setup

setup(
    setup_requires=['pbr'],
    pbr=True,
    py_modules=['htmlwrite', ],
    include_package_data=True,
    test_suite='test_htmlwrite',
)


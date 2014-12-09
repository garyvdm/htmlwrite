#!/usr/bin/env python

import setuptools

setuptools.setup(
    name='htmlwrite',
    py_modules=['htmlwrite', ],
    include_package_data=True,
    install_requires=['MarkupSafe', ],
    test_suite='test_htmlwrite',
)

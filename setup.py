#!/usr/bin/env python

import setuptools

with open('README.md') as f:
    readme = f.read()

setuptools.setup(
    name='htmlwrite',
    version='1.0',
    description='Write html to a file like object, using a pythonic syntax.',
    long_description=readme,
    url='https://github.com/garyvdm/htmlwrite',
    license='MIT',
    author='Gary van der Merwe',
    author_email='garyvdm@gmail.com',
    py_modules=['htmlwrite', ],
    include_package_data=True,
    install_requires=['MarkupSafe', ],
    test_suite='test_htmlwrite',
)

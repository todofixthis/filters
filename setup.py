# coding=utf-8
# :bc: Not importing unicode_literals because in Python 2 distutils,
# some values are expected to be byte strings.
from __future__ import absolute_import, division, print_function

from codecs import StreamReader, open
from sys import version_info

from setuptools import setup


##
# Check Python version.
if version_info[0:2] < (2, 7):
  raise EnvironmentError('Filters requires Python 2.7 or greater.')

if (version_info[0] == 3) and (version_info[1] < 5):
  raise EnvironmentError('Filters requires Python 3.5 or greater.')


##
# Determine dependencies, depending on Python version.
dependencies = [
    'python-dateutil',
    'pytz',
    'regex',
    'six',
]

if version_info[0] < 3:
    # noinspection SpellCheckingInspection
    dependencies.append('py2casefold')

if version_info[0:2] < (3, 5):
    dependencies.append('typing')


##
# Load long description for PyPi.
with open('README.rst', 'r', 'utf-8') as f: # type: StreamReader
    long_description = f.read()


##
# Off we go!
setup(
    name        = 'filters',
    description = 'Validation and data pipelines made easy!',
    url         = 'http://filters.readthedocs.io/',

    version = '1.1.4',

    packages = ['filters'],

    long_description = long_description,

    install_requires = dependencies,

    test_suite    = 'test',
    test_loader   = 'nose.loader:TestLoader',
    tests_require = [
        'nose',
    ],

    data_files = [
        ('', ['LICENSE']),
    ],

    license = 'MIT',

    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Text Processing :: Filters',
    ],

    keywords = 'data validation',

    author          = 'Phoenix Zerin',
    author_email    = 'phoenix.zerin@eflglobal.com',
)

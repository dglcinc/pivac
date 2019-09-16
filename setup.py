#!/usr/bin/env python

# (tailored from: https://github.com/pypa/sampleproject/blob/master/setup.py
from setuptools import setup, find_packages
from codecs import open
from os import path

# Get the long description from the README file
here = path.abspath(path.dirname(__file__))
with open(path.join(here, 'DESC.rst'), encoding='utf-8') as f:
    long_description = f.read()

setup (
  name='pivac',
  version='0.7.7',
  description='Raspberry Pi input utilities',
  long_description=long_description,

  url='https://github.com/dglcinc/pivac',
  license='MIT',
  classifiers=[
    'Development Status :: 4 - Beta',
    'License :: OSI Approved :: MIT License',
    'Programming Language :: Python :: 2.7'
  ],

  keywords='rpi raspberry pi signalk ted ted5000 redlink honeywell',

  author='David Lewis',
  author_email='david@dglc.com',

# before running this setup, apt install libxml2-dev libxslt-dev
packages=['pivac'],
  install_requires=['w1thermsensor','pytemperature','lxml','requests','mechanize','beautifulsoup4', 'PyYAML', 'soupsieve'],

  scripts=['scripts/provider.sh','scripts/pivac-provider.sh','scripts/pivac-provider.py','scripts/pivac'],
  data_files=[('/etc/pivac', ['config/config.yml.sample']),('/etc/pivac/signalk',['config/config.yml.flir','signalk/example_settings.json'])],
  python_requires='>=2.7'
)

#!/usr/bin/env python

# (tailored from: https://github.com/pypa/sampleproject/blob/master/setup.py
from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

setup (
  name='pivac',
  version='0.1.0',
  description='Raspberry Pi input utilities',

  url='https://github.com/dglcinc/pivac',
  license='MIT',
  classifiers=[
    'Development Status :: 4 - Beta',
    'License :: MIT License',
    'Programming Language :: Python :: 2.7'
  ],

  keywords='rpi raspberry pi signalk ted ted5000 redlink honeywell',

  author='David Lewis',
  author_email='david@dglc.com',

  packages=['pivac'],
  install_requires=['w1thermsensor','pytemperature','lxml','requests','mechanize','beautifulsoup4'],

  scripts=['scripts/sk-provider.sh','scripts/sk-pivac-provider.sh','scripts/sk-pivac-provider.py'],
  data_files=[('config', ['config/config.json.sample'])],
  python_requires='>=2.7'
)

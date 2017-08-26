#!/usr/bin/env python

# (tailored from: https://github.com/pypa/sampleproject/blob/master/setup.py
from setuptools import setup, find_packages
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

setup (
  name='pivac',
  version='0.6.0',
  shortdesc='Raspberry Pi input utilities',
  longdesc=read_file("DESC.rst"),

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

  packages=['pivac'],
  install_requires=['w1thermsensor','pytemperature','lxml','requests','mechanize','beautifulsoup4', 'PyYAML'],

  scripts=['scripts/sk-provider.sh','scripts/sk-pivac-provider.sh','scripts/sk-pivac-provider.py'],
  data_files=[('/etc/pivac', ['config/config.yml.sample'])],
  python_requires='>=2.7'
)

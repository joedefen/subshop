#!/usr/bin/env python3
"""
Setup script for the 'subshop' project.

Some ways to use this script...

=== Ensure setuptools is up-to-date:

 $ python -m pip install --upgrade setuptools # update setuptools

=== Install into vitualenv (editable)

 $ cd ~/subshop # or wherever the project dir resides
 $ python -m venv .venv
 $ source .venv/bin/activate
 $ pip install -e . # '-e' for editable
 $ # run tests and use
 # deactivate # disable virtualenv
 $ rm -rf .venv # cleanup virtualenv

=== Install into home directory 

 $ cd ~/subshop # or wherever the project dir resides
 $ pip install . --user # add '-e' for editable

"""
from setuptools import setup

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name = 'subshop',
    version = '0.1.0',
    license = 'MIT',
    description = 'tools to download, clean, and synchronize subtitles',
    author = 'Joe Defen',
    author_email = 'joe@jdef.ga',
    url = 'https://github.com/joedefen/subshop',
    download_url = 'TBD',
    scripts = ['subshop', 'video2srt', 'subs-cronjob'],
    packages = ['LibSub', 'LibGen'],
    classifiers = [
        'Development Status :: 4 - Beta',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 3',
        'Intended Audience :: End Users/Desktop',
        ],
    install_requires=requirements,
    )

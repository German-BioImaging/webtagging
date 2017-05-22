#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
from setuptools import setup, find_packages


# Utility function to read the README file. Also support json content
def read_file(fname, content_type=None):
    dir_path = os.path.dirname(os.path.realpath(__file__))
    p = os.path.join(dir_path, fname)
    with open(p) as f:
        if content_type in ('json',):
            data = json.load(f)
        else:
            data = f.read()
    return data


VERSION = read_file('VERSION.txt').strip()
DESCRIPTION = 'OMERO webtagging tagsearch app'
AUTHOR = 'D.P.W. Russell'
LICENSE = 'AGPL-3.0'
HOMEPAGE = 'https://github.com/MicronOxford/webtagging'

setup(
    name='omero-webtagging-tagsearch',
    packages=find_packages(exclude=['ez_setup']),
    version=VERSION,
    description=DESCRIPTION,
    long_description=read_file('README.rst'),
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Environment :: Web Environment',
        'Framework :: Django',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU Affero General Public License v3',
        'Natural Language :: English',
        'Operating System :: OS Independent',
        'Programming Language :: JavaScript',
        'Programming Language :: Python :: 2',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        'Topic :: Internet :: WWW/HTTP :: WSGI',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Software Development :: Libraries :: '
        'Application Frameworks',
        'Topic :: Text Processing :: Markup :: HTML'
    ],
    author=AUTHOR,
    author_email='douglas_russell@hms.harvard.edu',
    license=LICENSE,
    url=HOMEPAGE,
    download_url='%s/archive/v%s.tar.gz' % (HOMEPAGE, VERSION),
    keywords=['OMERO.web', 'webtagging', 'tagsearch'],
    install_requires=[],
    include_package_data=True,
    zip_safe=False
)

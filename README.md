OMERO.webtagging
================

Requirements
============

* OMERO 4.4.0 or later
* Python 2.6 or later

Installation
============

Clone the repository in to your OMERO.web installation:

    cd <dist>/lib/python/omeroweb # for production, or for development: <openmicroscopy checkout>components/tools/OmeroWeb/omeroweb/
    git clone git://github.com/dpwrussell/webtagging.git
    path/to/bin/omero config set omero.web.apps '["webtagging"]'

Now start up OMERO.web as normal in your development environment.

Documentation
=============

http://www.openmicroscopy.org/site/support/partner/omero.webtagging

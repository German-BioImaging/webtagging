OMERO.webtagging
================

Requirements
============

* OMERO 4.4.0 or later
* Python 2.6 or later

Installation
============

Clone the repository in to your OMERO.web installation.

    cd <dist>/lib/python/omeroweb # for production, or for development: <openmicroscopy checkout>components/tools/OmeroWeb/omeroweb/
    git clone git://github.com/dpwrussell/webtagging.git
    path/to/bin/omero config set omero.web.apps '["webtagging"]'
    # For OMERO 5 and above only:
    path/to/bin/omero config set omero.web.ui.center_plugins '[["Auto Tag", "webtagging/auto_tag_init.js.html", "auto_tag_panel"]]'

Now start up OMERO.web as normal in your development environment.

Note: Instead of cloning directly into OMERO.web it's also possible to clone to any location and then add webtagging to the PYTHONPATH as documented [here](https://www.openmicroscopy.org/site/support/omero5/developers/Web/CreateApp.html#add-your-app-location-to-your-pythonpath).

Documentation
=============

http://www.openmicroscopy.org/site/support/partner/omero.webtagging

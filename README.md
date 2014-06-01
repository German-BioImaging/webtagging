webtagging_search
=================

Tag Search based on set intersections

Requirements
============

* OMERO 5.0.0 or later
* Python 2.6 or later

Installation
============

Clone the repository in to your OMERO.web installation:

    cd <dist>/lib/python/omeroweb # for production, or for development: <openmicroscopy checkout>components/tools/OmeroWeb/omeroweb/
    git clone git://github.com/dpwrussell/webtagging_search.git webtagging_search
    path/to/bin/omero config set omero.web.apps '["webtagging_search"]'

To add the 'Tag Search' link to the top links bar:

    omero config append omero.web.ui.top_links '"Tag Search", "tagsearch"'

Now start up OMERO.web as normal in your development environment. The search page will be accessible at the 'Tag Search' link on the top links bar.

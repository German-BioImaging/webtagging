webtagging_search
=================

Tag Search based on set intersections

Requirements
============

* OMERO 4.4.0 or later
* Python 2.6 or later

Installation
============

Clone the repository in to your OMERO.web installation:

    cd <dist>/lib/python/omeroweb # for production, or for development: <openmicroscopy checkout>components/tools/OmeroWeb/omeroweb/
    git clone git://github.com/dpwrussell/webtagging_search.git
    path/to/bin/omero config set omero.web.apps '["webtagging_search"]'

This isn't plumbed automatically into any part of webclient yet, so to get access to the search, add to ```components/tools/OmeroWeb/omeroweb/urls.py```

    (r'(?i)^tagsearch/', include('omeroweb.webtagging_search.urls')),

Now start up OMERO.web as normal in your development environment. The search page will be available at a url like: http://localhost:8000/webtagging_search/

OMERO.webtagging
================

This now is composed of two tools: autotag and tagsearch.

Requirements
============

* OMERO 4.4.0 or later
* Python 2.6 or later

Installation
============

Documentation for using PYTHONPATH to allow omero to find webapps is [here](https://www.openmicroscopy.org/site/support/omero5/developers/Web/CreateApp.html#add-your-app-location-to-your-pythonpath).

Clone the repository in to a location outsude of the Omero.Web installation, e.g. ```~/Checkout/webtagging```

    cd Checkout
    git clone git://github.com/MicronOxford/webtagging.git webtagging

Add this location to the PYTHONPATH

    export PYTHONPATH=~/Checkout/webtagging:$PYTHONPATH

Add autotag to webclient

    # For OMERO 5 and above only:
    omero config append omero.web.apps '"autotag"'
    omero config append omero.web.ui.center_plugins '["Auto Tag", "autotag/auto_tag_init.js.html", "auto_tag_panel"]'

    # For OMERO 4.4.x:
    omero config set omero.web.apps '["autotag"]' Don't forget to add your existing web apps to this list.

Add tagsearch to webclient

    # For OMERO 5 and above only:
    omero config append omero.web.apps '"tagsearch"'
    omero config append omero.web.ui.top_links '["Tag Search", "tagsearch"]'

    # For OMERO 4.4.x:
    omero config set omero.web.apps '["tagsearch"]' # Don't forget to add your existing web apps to this list. e.g. '["autotag", "tagsearch"]'
    omero config set omero.web.ui.top_links '[["Tag Search", "tagsearch"]]' # Don't forget to add any existing top links to the list, '[["Figure", "figure_index"], ["Tag Search", "tagsearch"]]''

Now start up OMERO.web as normal

Documentation
=============

http://www.openmicroscopy.org/site/support/partner/omero.webtagging

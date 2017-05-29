Installation
============

The recommended way to install tagsearch is using `pip`, but it is also possible
to install it manually as described `here <https://www.openmicroscopy.org/site/support/omero5/developers/Web/CreateApp.html#add-your-app-location-to-your-pythonpath>`_.

::

  # In the python environment of OMERO.web (virtualenv or global)
  pip install omero-webtagging-tagsearch

  # Add tagsearch to webclient
  omero config append omero.web.apps '"omero_webtagging_tagsearch"'

  # Add a top-link to tagsearch designer
  omero config append omero.web.ui.top_links '["Tag Search", "tagsearch"]'


Documentation
=============

Available on the `OMERO website <http://www.openmicroscopy.org/site/support/partner/omero.webtagging>`_.


Development
===========

Pure javascript so does not require a node build step.

To install using pip in development mode (in appropriate virtualenv)

::
  # In the top-level tagsearch directory containing setup.py
  pip install -e .
  cd $OMERO_PREFIX

OMERO development server can then be started in the usual way. Remember to
configure the tagsearch settings the same as above.

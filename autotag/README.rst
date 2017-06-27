Installation
============

The recommended way to install autotag is using `pip`, but it is also possible
to install it manually as described `here <https://www.openmicroscopy.org/site/support/omero5/developers/Web/CreateApp.html#add-your-app-location-to-your-pythonpath>`_.

::

  # In the python environment of OMERO.web (virtualenv or global)
  pip install omero-webtagging-autotag

  # Add autotag to webclient
  omero config append omero.web.apps '"omero_webtagging_autotag"'

  # Add autotag to centre panel
  omero config append omero.web.ui.center_plugins '["Auto Tag", "omero_webtagging_autotag/auto_tag_init.js.html", "auto_tag_panel"]'


Documentation
=============

Available on the `OMERO website <http://help.openmicroscopy.org/web-tagging.html>`_.


Development
===========

Uses node and webpack.

This will detect changes and rebuild `static/autotag/js/bundle.js` when there
are any. This works in conjunction with django development server as that
will be monitoring `bundle.js` for any changes.

To build the node components on changes

::

  cd omero_webtagging_autotag
  npm install
  node_modules/webpack/bin/webpack.js --watch

To install using pip in development mode (in appropriate virtualenv)

::

  # In the top-level autotag directory containing setup.py
  pip install -e .
  cd $OMERO_PREFIX

OMERO development server can then be started in the usual way. Remember to
configure the autotag settings the same as above.


# This settings.py file will be imported by omero.settings file AFTER it has initialised custom settings.
from django.conf import settings

# We can directly manipulate the settings
# E.g. add plugins to RIGHT_PLUGINS list
settings.CENTER_PLUGINS.append(["Auto Tag", "webtagging/auto_tag_init.js.html", "auto_tag_panel"])

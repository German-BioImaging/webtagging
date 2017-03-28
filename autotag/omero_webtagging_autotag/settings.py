# This settings.py file will be imported by omero.settings file AFTER it has initialised custom settings.
import django

# Old style
if django.VERSION < (1, 6):
    from django.conf import settings

    # We can directly manipulate the settings
    # E.g. add plugins to RIGHT_PLUGINS list
    settings.CENTER_PLUGINS.append(["Auto Tag", "omero_webtagging_autotag/auto_tag_init.js.html", "auto_tag_panel"])

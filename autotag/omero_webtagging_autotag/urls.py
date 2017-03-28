from django.conf.urls import url, patterns

from . import views

urlpatterns = patterns(
    'django.views.generic.simple',

    url(r'^get_image_detail_and_tags/$',
        views.get_image_detail_and_tags,
        name="webtagging_get_image_detail_and_tags"),

    # process main form submission
    url(r'^auto_tag/processUpdate/$',
        views.process_update,
        name="webtagging_process_update"),

    # Create tags for tags dialog
    url(r'^create_tag/$',
        views.create_tag,
        name="webtagging_create_tag"),

)

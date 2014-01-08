import django
if django.VERSION < (1, 6):
    from django.conf.urls.defaults import *
else:
    from django.conf.urls import *

from . import views

urlpatterns = patterns('django.views.generic.simple',

    # index 'home page' of the webtagging app
    url( r'^$', views.index, name='webtagging_index' ),

    # name tokens to tags
    url( r'^auto_tag/dataset/(?P<datasetId>[0-9]+)/$', views.auto_tag, name="webtagging_auto_tag" ),

    # process main form submission
    url( r'^auto_tag/processUpdate/$', views.process_update, name="webtagging_process_update" ),

    # list & create tags for tags dialog
    url( r'^list_tags/$', views.list_tags, name="webtagging_list_tags" ),
    url( r'^create_tag/$', views.create_tag, name="webtagging_create_tag" ),

    # determine if images have a certain tag
    url( r'^get_tag_on_images/$', views.get_tag_on_images, name="webtagging_get_tag_on_images" ),

)

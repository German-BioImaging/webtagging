from django.conf.urls.defaults import *

from omeroweb.webtagging import views

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
)

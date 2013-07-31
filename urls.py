from django.conf.urls.defaults import *

from omeroweb.webtagging import views

urlpatterns = patterns('django.views.generic.simple',

    # index 'home page' of the webtagging app
    url( r'^$', views.index, name='webtagging_index' ),

    # name tokens to tags
    url( r'^tags_from_names/dataset/(?P<datasetId>[0-9]+)/$', views.tags_from_names, name="tags_from_names" )

)

from django.conf.urls.defaults import *

from . import views

urlpatterns = patterns('django.views.generic.simple',

    # index 'home page' of the webtagging app
    url( r'^$', views.TagSearchFormView.as_view(), name='wtsindex' ),
    url( r'^images$', views.TagImageSearchView.as_view(), name='wtsimages' ),
    
)

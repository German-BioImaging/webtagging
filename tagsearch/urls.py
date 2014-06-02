from django.conf.urls import patterns, url, include

from . import views

urlpatterns = patterns('django.views.generic.simple',

    # index 'home page' of the webtagging app
    url( r'^$', views.index, name='tagsearch' ),

    # index 'home page' of the webtagging app
    # url( r'^$', views.TagSearchFormView.as_view(), name='wtsindex' ),
    url( r'^images$', views.tag_image_search, name='wtsimages' ),
    
)

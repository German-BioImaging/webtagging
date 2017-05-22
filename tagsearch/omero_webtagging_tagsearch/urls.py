from django.conf.urls import url, patterns

from . import views

urlpatterns = patterns(
    'django.views.generic.simple',

    # index 'home page' of the webtagging app
    url(r'^$', views.index, name='tagsearch'),

    # index 'home page' of the webtagging app
    url(r'^images$', views.tag_image_search, name='wtsimages'),

)

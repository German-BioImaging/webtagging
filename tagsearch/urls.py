from django.conf.urls import patterns, url, include

from . import views

urlpatterns = patterns('django.views.generic.simple',

    # index 'home page' of the webtagging app
    url( r'^$', views.index, name='tagsearch' ),

    # index 'home page' of the webtagging app
    # url( r'^$', views.TagSearchFormView.as_view(), name='wtsindex' ),
    url( r'^images$', views.tag_image_search, name='wtsimages' ),

    # 'Replacement for the standard OMERO view'
    url( r'^data$', views.load_template, {'menu':'userdata'}, name="wtsdata" ),
    url( r'^load_data/(?:(?P<o1_type>((?i)project|dataset|image|screen|plate|well|orphaned))/)?(?:(?P<o1_id>[0-9]+)/)?(?:(?P<o2_type>((?i)dataset|image|plate|acquisition|well))/)?(?:(?P<o2_id>[0-9]+)/)?(?:(?P<o3_type>((?i)image|well))/)?(?:(?P<o3_id>[0-9]+)/)?$', views.load_data, name="wtsload_data" ),


    # API
    url( r'^api/tagsearch_images$', views.tagsearch_images, name='tagsearch_images' )
    
)

import json

from django.http import HttpResponse
from django.views.generic.base import View
from django.views.generic import TemplateView, FormView
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse
from django.shortcuts import render, render_to_response
from django.template.loader import render_to_string

from omeroweb.webclient.decorators import render_response, login_required
from omero.gateway import TagAnnotationWrapper
from omero.sys import Parameters
from omero.rtypes import rlong, rlist

from .forms import TagSearchForm

import logging

logger = logging.getLogger(__name__)

class TagSearchFormView(FormView):
    """
    Form view to present form for tag--based navigation
    """
    template_name = 'webtagging_search/tagsearch.html'
    form_class = TagSearchForm

    def get_success_url(self):
        return reverse('wtsindex')

    def get_context_data(self, **kwargs):
        context = super(TagSearchFormView, self).get_context_data(**kwargs)

        from json import JSONEncoder
        class JSONSetEncoder(JSONEncoder):
            def default(self, obj):
                if isinstance(obj, set):
                    return list(obj)
                return JSONEncoder.default(self, obj)

        context['tag_intersections'] = json.dumps(self.tag_intersections, cls=JSONSetEncoder)
        return context


    def get_form_kwargs(self):
        kwargs = super(TagSearchFormView, self).get_form_kwargs()

        self.tag_intersections = {}
        tags = set()

        params = Parameters()
        qs = self.conn.getQueryService()

        def process_links(class_name):

            hql = "select annLink from %sAnnotationLink as annLink " \
                  "join fetch annLink.child as ann " \
                  "where ann.class = TagAnnotation" % class_name
            # TODO Investigate how big returned data is for large datasets?
            ann_links = qs.findAllByQuery(hql, params)

            # Build a mapping of images to tags and update the tag set
            containers = {}

            for ann_link in ann_links:
                containers.setdefault(
                    ann_link.getParent().getId().val,
                    set([])
                ).add(ann_link.getChild().getId().val)

                tags.add( (ann_link.getChild().getId().val,
                           ann_link.child.getTextValue().val) )

            # Use the mapping to add the intersections
            for container_id, container_tag_ids in containers.iteritems():
                # For each item in the set, append all the other items to it's entry
                for tag_id in container_tag_ids:
                    # Add the other tags to the set of intersections for this tag
                    self.tag_intersections.setdefault(tag_id, set([])).update(
                        container_tag_ids.symmetric_difference([tag_id]))

        # There is no hibernate union, so it is necessary to do 3 queries
        process_links('Image')
        process_links('Dataset')
        process_links('Project')

        # Get tags
        # tags = list(self.conn.getObjects("TagAnnotation"))
        # Convert the set to a list so it can be sorted
        tags = list(tags)
        # Sort tags
        tags.sort(key=lambda x: x[1].lower())

        kwargs['tags'] = tags
        # kwargs['tag_intersections'] = tag_intersections
        kwargs['conn'] = self.conn
        return kwargs

    def form_valid(self, form):
        # Actually unlikely we'll ever submit this form
        print('called form_valid')
        return super(TagSearchFormView, self).form_valid(form)

    @method_decorator(login_required(setGroupContext=True))
    def dispatch(self, *args, **kwargs):
        # Get OMERO connection
        self.conn = kwargs.get('conn', None)
        return super(TagSearchFormView, self).dispatch(*args, **kwargs)

@login_required(setGroupContext=True)
# @render_response()
def tag_image_search(request, conn=None, **kwargs):
    if request.method == "POST":

        selected_tags = [long(x) for x in request.POST.getlist('selectedTags')]
        results_preview = bool(request.POST.get('results_preview'))

        def getObjectsWithAllAnnotations(obj_type, annids):
            # Get the images that match
            hql = "select link.parent.id from %sAnnotationLink link " \
                  "inner join link.child as ann " \
                  "where ann.id in (:oids) " \
                  "group by link.parent.id " \
                  "having count(link.child.id) = %s" %  (obj_type, len(annids))
            params = Parameters()
            params.map = {}
            params.map["oids"] = rlist([rlong(o) for o in set(annids)])

            qs = conn.getQueryService()
            return [x[0].getValue() for x in qs.projection(hql,params)]

        context = {}
        if selected_tags:
            image_ids = getObjectsWithAllAnnotations('Image', selected_tags)
            context['image_count'] = len(image_ids)
            dataset_ids = getObjectsWithAllAnnotations('Dataset', selected_tags)
            context['dataset_count'] = len(dataset_ids)
            project_ids = getObjectsWithAllAnnotations('Project', selected_tags)
            context['project_count'] = len(project_ids)


            if results_preview:
                if image_ids:
                    images = conn.getObjects('Image', ids = image_ids)
                    context['images'] = [ { 'id':x.getId(), 'name':x.getName() } for x in images]

                if dataset_ids:
                    datasets = conn.getObjects('Dataset', ids = dataset_ids)
                    context['datasets'] = [{ 'id':x.getId(), 'name':x.getName() } for x in datasets]

                if project_ids:
                    projects = conn.getObjects('Project', ids = project_ids)
                    context['projects'] = [{ 'id':x.getId(), 'name':x.getName() } for x in projects]

        logger.error("HERE1")
        html_response = render_to_string("webtagging_search/image_results.html", context)
        logger.error("HERE2")

        
        # Calculate remaining possible tag navigations
        # TODO Remove above queries and instead use/modify this query to get
        # the data
        annids = selected_tags

        sub_hql = "select parent from ImageAnnotationLink link " \
                  "join link.child as child " \
                  "join link.parent as parent " \
                  "where child.id in (:oids) " \
                  "group by parent.id " \
                  "having count(link) = %s" % len(annids)

        hql = "select image from Image image " \
              "join fetch image.annotationLinks as annLink " \
              "join fetch annLink.child as ann " \
              "where image in (%s)" % sub_hql


        params = Parameters()
        params.map = {}
        params.map["oids"] = rlist([rlong(o) for o in set(annids)])

        qs = conn.getQueryService()
        results = qs.findAllByQuery(hql, params)
        
        # Calculate the remaining possible tags
        remaining = set([])
        for result in results:
            for ann in result.iterateAnnotationLinks():
                remaining.add(ann.getChild().getId().val)
        
        logger.error("HERE3")
        # Return the navigation data and the html preview for display
        # return {"navdata": list(remaining), "html": html_response}
        return HttpResponse(json.dumps({"navdata": [1,2,3], "html": html_response}), content_type="application/json")

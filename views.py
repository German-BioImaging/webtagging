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

    def get_form_kwargs(self):
        kwargs = super(TagSearchFormView, self).get_form_kwargs()

        # List of tuples (id, value)
        tags = []

        params = Parameters()
        qs = self.conn.getQueryService()

        # Get tags
        # It is not sufficient to simply get the objects as there may be tags
        # which are not applied which don't really make sense to display
        # tags = list(self.conn.getObjects("TagAnnotation"))
        hql = "select distinct link.child.id, link.child.textValue " \
              "from ImageAnnotationLink link " \
              "where link.child.class is TagAnnotation " \
              "order by link.child.textValue"
        tags = [(result[0].val, result[1].val) for result in qs.projection(hql, params)]

        # Sort tags
        # TODO Should be able to do this in the database query but for some 
        # reason using lower on the order by requires that the select also be
        # lower.
        tags.sort(key=lambda x: x[1].lower())

        kwargs['tags'] = tags
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
# TODO Figure out what happened to render_response as it wasn't working on
# production
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

        html_response = render_to_string("webtagging_search/image_results.html", context)

        # Calculate remaining possible tag navigations
        sub_hql = "select link.parent.id from ImageAnnotationLink link " \
               "where link.child.id in (:oids) " \
               "group by link.parent.id " \
               "having count (link.parent) = %s" % len(selected_tags)

        hql = "select distinct link.child.id from ImageAnnotationLink link " \
           "where link.parent.id in (%s)" % sub_hql

        params = Parameters()
        params.map = {}
        params.map["oids"] = rlist([rlong(o) for o in set(selected_tags)])

        qs = conn.getQueryService()
        results = qs.projection(hql, params)
        
        remaining = []
        for result in results:
            remaining.append(result[0].val)

        # Return the navigation data and the html preview for display
        # return {"navdata": list(remaining), "html": html_response}
        return HttpResponse(json.dumps({"navdata": remaining,
                                        "html": html_response}),
                            content_type="application/json")

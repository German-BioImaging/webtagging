import json

from django.http import HttpResponse
from django.views.generic.base import View
from django.views.generic import TemplateView, FormView
from django.utils.decorators import method_decorator
from django.core.urlresolvers import reverse

from omeroweb.webclient.decorators import render_response, login_required
from omero.gateway import TagAnnotationWrapper
from omero.sys import Parameters
from omero.rtypes import rlong, rlist

from .forms import TagSearchForm

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

        # Get all images
        images = list(self.conn.getObjects("Image"))

        # TODO If there are huge number of tags and images, could look at
        # avoiding duplication temporarily by using a generator. Probably if
        # that is the case, a whole new approach will be needed anyway.
        self.tag_intersections = {}
        tags = set()

        # Get tags in those images
        for image in images:
            # Turn only the TagAnnotations into a set
            tag_ids_in_image = set([])
            for tag in image.listAnnotations():
                if isinstance(tag, TagAnnotationWrapper):
                    tag_ids_in_image.add(tag.getId())
                    tags.add((tag.getId(), tag.getValue()))
            # For each item in the set, append all the other items to it's entry
            for tag_id in tag_ids_in_image:
                # Add the other tags to the set of intersections for this tag
                self.tag_intersections.setdefault(tag_id, set([])).update(
                    tag_ids_in_image.symmetric_difference([tag_id]))

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


class TagImageSearchView(TemplateView):
    template_name = 'webtagging_search/image_results.html'

    # def get(self, request, *args, **kwargs):
    #     print('Probably should never be GET here')
    #     print('get args: %s' %  request.POST['selectedTags'])
    #     context = self.get_context_data(**kwargs)
    #     return self.sender_to_response(context)

    def post(self, request, *args, **kwargs):
        selected_tags = [long(x) for x in request.POST.getlist('selectedTags')]
        results_preview = bool(request.POST.get('results_preview'))

        def getObjectsWithAllAnnotations(conn, obj_type, annids):
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

        context = self.get_context_data(**kwargs)
        if selected_tags:
            image_ids = getObjectsWithAllAnnotations(self.conn, 'Image', selected_tags)
            context['image_count'] = len(image_ids)
            dataset_ids = getObjectsWithAllAnnotations(self.conn, 'Dataset', selected_tags)
            context['dataset_count'] = len(dataset_ids)
            project_ids = getObjectsWithAllAnnotations(self.conn, 'Project', selected_tags)
            context['project_count'] = len(project_ids)


            if results_preview:
                if image_ids:
                    images = self.conn.getObjects('Image', ids = image_ids)
                    context['images'] = [ { 'id':x.getId(), 'name':x.getName() } for x in images]

                if dataset_ids:
                    datasets = self.conn.getObjects('Dataset', ids = dataset_ids)
                    context['datasets'] = [{ 'id':x.getId(), 'name':x.getName() } for x in datasets]

                if project_ids:
                    projects = self.conn.getObjects('Project', ids = project_ids)
                    context['projects'] = [{ 'id':x.getId(), 'name':x.getName() } for x in projects]

        print 'returning'
        return self.render_to_response(context)

    @method_decorator(login_required(setGroupContext=True))
    def dispatch(self, *args, **kwargs):
        # Get OMERO connection
        self.conn = kwargs.get('conn', None)
        return super(TagImageSearchView, self).dispatch(*args, **kwargs)


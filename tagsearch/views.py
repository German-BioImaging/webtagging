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

from omeroweb.webclient.forms import  GlobalSearchForm, ShareForm, BasketShareForm, \
                    ContainerForm, ContainerNameForm, ContainerDescriptionForm, \
                    CommentAnnotationForm, TagsAnnotationForm, \
                    UsersForm, \
                    MetadataFilterForm, MetadataDetectorForm, MetadataChannelForm, \
                    MetadataEnvironmentForm, MetadataObjectiveForm, MetadataObjectiveSettingsForm, MetadataStageLabelForm, \
                    MetadataLightSourceForm, MetadataDichroicForm, MetadataMicroscopeForm, \
                    FilesAnnotationForm, WellIndexForm

from .forms import TagSearchForm

import logging

logger = logging.getLogger(__name__)

@login_required()
@render_response()
def index(request, conn=None, **kwargs):
    request.session.modified = True

    # TODO Hardcode menu as search until I figure out what to do with menu
    menu = 'search'
    template = "tagsearch/tagnav.html"


    #tree support
    init = {'initially_open':None, 'initially_select': []}
    first_sel = None
    initially_open_owner = None
    # E.g. backwards compatible support for path=project=51|dataset=502|image=607 (select the image)
    path = request.REQUEST.get('path', '')
    i = path.split("|")[-1]
    if i.split("=")[0] in ('project', 'dataset', 'image', 'screen', 'plate', 'tag'):
        init['initially_select'].append(str(i).replace("=",'-'))  # Backwards compatible with image=607 etc
    # Now we support show=image-607|image-123  (multi-objects selected)
    show = request.REQUEST.get('show', '')
    for i in show.split("|"):
        if i.split("-")[0] in ('project', 'dataset', 'image', 'screen', 'plate', 'tag', 'acquisition', 'run', 'well'):
            i = i.replace('run', 'acquisition')   # alternatives for 'acquisition'
            init['initially_select'].append(str(i))
    if len(init['initially_select']) > 0:
        # tree hierarchy open to first selected object
        init['initially_open'] = [ init['initially_select'][0] ]
        first_obj, first_id = init['initially_open'][0].split("-",1)
        # if we're showing a tag, make sure we're on the tags page...
        if first_obj == "tag" and menu != "usertags":
            return HttpResponseRedirect(reverse(viewname="load_template", args=['usertags']) + "?show=" + init['initially_select'][0])
        try:
            conn.SERVICE_OPTS.setOmeroGroup('-1')   # set context to 'cross-group'
            if first_obj == "tag":
                first_sel = conn.getObject("TagAnnotation", long(first_id))
            else:
                first_sel = conn.getObject(first_obj, long(first_id))
                initially_open_owner = first_sel.details.owner.id.val
                # Wells aren't in the tree, so we need parent...
                if first_obj == "well":
                    parentNode = first_sel.getWellSample().getPlateAcquisition()
                    ptype = "acquisition"
                    if parentNode is None:      # No Acquisition for this well...
                        parentNode = first_sel.getParent()  #...use Plate instead
                        ptype = "plate"
                    first_sel = parentNode
                    init['initially_open'] = ["%s-%s" % (ptype, parentNode.getId())]
                    init['initially_select'] = init['initially_open'][:]
        except:
            pass    # invalid id
        if first_obj not in ("project", "screen"):
            # need to see if first item has parents
            if first_sel is not None:
                for p in first_sel.getAncestry():
                    if first_obj == "tag":  # parents of tags must be tags (no OMERO_CLASS)
                        init['initially_open'].insert(0, "tag-%s" % p.getId())
                    else:
                        init['initially_open'].insert(0, "%s-%s" % (p.OMERO_CLASS.lower(), p.getId()))
                        initially_open_owner = p.details.owner.id.val
                if init['initially_open'][0].split("-")[0] == 'image':
                    init['initially_open'].insert(0, "orphaned-0")
    # need to be sure that tree will be correct omero.group
    if first_sel is not None:
        switch_active_group(request, first_sel.details.group.id.val)

    # search support
    global_search_form = GlobalSearchForm(data=request.REQUEST.copy())
    if menu == "search":
        if global_search_form.is_valid():
            init['query'] = global_search_form.cleaned_data['search_query']

    # get url without request string - used to refresh page after switch user/group etc
    url = reverse(viewname="tagsearch")

    # validate experimenter is in the active group
    active_group = request.session.get('active_group') or conn.getEventContext().groupId
    # prepare members of group...
    s = conn.groupSummary(active_group)
    leaders = s["leaders"]
    members = s["colleagues"]
    userIds = [u.id for u in leaders]
    userIds.extend( [u.id for u in members] )
    users = []
    if len(leaders) > 0:
        users.append( ("Owners", leaders) )
    if len(members) > 0:
        users.append( ("Members", members) )
    users = tuple(users)

    # check any change in experimenter...
    user_id = request.REQUEST.get('experimenter')
    if initially_open_owner is not None:
        if (request.session.get('user_id', None) != -1): # if we're not already showing 'All Members'...
            user_id = initially_open_owner
    try:
        user_id = long(user_id)
    except:
        user_id = None
    if user_id is not None:
        print('form_users')
        form_users = UsersForm(initial={'users': users, 'empty_label':None, 'menu':menu}, data=request.REQUEST.copy())
        if not form_users.is_valid():
            if user_id != -1:           # All users in group is allowed
                user_id = None
    if user_id is None:
        # ... or check that current user is valid in active group
        user_id = request.session.get('user_id', None)
        if user_id is None or int(user_id) not in userIds:
            if user_id != -1:           # All users in group is allowed
                user_id = conn.getEventContext().userId

    request.session['user_id'] = user_id

    if conn.isAdmin():  # Admin can see all groups
        myGroups = [g for g in conn.getObjects("ExperimenterGroup") if g.getName() not in ("user", "guest")]
    else:
        myGroups = list(conn.getGroupsMemberOf())
    myGroups.sort(key=lambda x: x.getName().lower())
    new_container_form = ContainerForm()

    # Create and set the form

    params = Parameters()
    qs = conn.getQueryService()
    service_opts = conn.SERVICE_OPTS.copy()
    service_opts.setOmeroGroup(active_group)

    def get_tags(obj):

        # Get tags
        # It is not sufficient to simply get the objects as there may be tags
        # which are not applied which don't really make sense to display
        # tags = list(self.conn.getObjects("TagAnnotation"))
        hql = "select distinct link.child.id, link.child.textValue " \
              "from %sAnnotationLink link " \
              "where link.child.class is TagAnnotation " \
              "order by link.child.textValue" % obj

        return [(result[0].val, result[1].val) for result in qs.projection(hql, params, service_opts)]

    # List of tuples (id, value)
    tags = set(get_tags('Image'))
    print('images', tags)
    tags.update(get_tags('Dataset'))
    print('datasets', tags)
    tags.update(get_tags('Project'))
    print('projects', tags)

    # Convert back to an ordered list and sort
    tags = list(tags)
    tags.sort(key=lambda x: x[1].lower())

    form = TagSearchForm(tags, conn)

    context = {'init':init, 'myGroups':myGroups, 'new_container_form':new_container_form, 'global_search_form':global_search_form}
    context['groups'] = myGroups
    context['active_group'] = conn.getObject("ExperimenterGroup", long(active_group))
    for g in context['groups']:
        g.groupSummary()    # load leaders / members
    context['active_user'] = conn.getObject("Experimenter", long(user_id))

    context['isLeader'] = conn.isLeader()
    context['current_url'] = url
    context['template'] = template
    context['tagnav_form'] = form

    return context

@login_required(setGroupContext=True)
# TODO Figure out what happened to render_response as it wasn't working on
# production
# @render_response()
def tag_image_search(request, conn=None, **kwargs):
    import time
    start = time.time()
    if request.method == "POST":

        selected_tags = [long(x) for x in request.POST.getlist('selectedTags')]
        results_preview = bool(request.POST.get('results_preview'))

        # validate experimenter is in the active group
        active_group = request.session.get('active_group') or conn.getEventContext().groupId
        service_opts = conn.SERVICE_OPTS.copy()
        service_opts.setOmeroGroup(active_group)

        def getObjectsWithAllAnnotations(obj_type, annids):
            # Get the images that match
            hql = "select link.parent.id from %sAnnotationLink link " \
                  "where link.child.id in (:oids) " \
                  "group by link.parent.id " \
                  "having count (distinct link.child) = %s" % (obj_type, len(annids))
            params = Parameters()
            params.map = {}
            params.map["oids"] = rlist([rlong(o) for o in set(annids)])

            qs = conn.getQueryService()
            return [x[0].getValue() for x in qs.projection(hql,params,service_opts)]

        context = {}
        html_response = ''
        remaining = set([])

        manager = {'containers': {}}
        preview = False
        project_count = 0
        dataset_count = 0
        image_count = 0

        if selected_tags:
            image_ids = getObjectsWithAllAnnotations('Image', selected_tags)
            context['image_count'] = len(image_ids)
            image_count = len(image_ids)
            dataset_ids = getObjectsWithAllAnnotations('Dataset', selected_tags)
            context['dataset_count'] = len(dataset_ids)
            dataset_count = len(dataset_ids)
            project_ids = getObjectsWithAllAnnotations('Project', selected_tags)
            context['project_count'] = len(project_ids)
            project_count = len(project_ids)

            if results_preview:
                if image_ids:
                    images = conn.getObjects('Image', ids = image_ids)
                    manager['containers']['images'] = list(images)

                if dataset_ids:
                    datasets = conn.getObjects('Dataset', ids = dataset_ids)
                    manager['containers']['datasets'] = list(datasets)

                if project_ids:
                    projects = conn.getObjects('Project', ids = project_ids)
                    manager['containers']['projects'] = list(projects)

                manager['c_size'] = len(image_ids) + len(dataset_ids) + len(project_ids)
                if manager['c_size'] > 0:
                    preview = True

            context['manager'] = manager

            html_response = render_to_string("tagsearch/search_details.html", context)

            middle = time.time()

            def getAnnotationsForObjects(obj_type, oids):
                # Get the images that match
                hql = "select distinct link.child.id from %sAnnotationLink link " \
                      "where link.parent.id in (:oids)" % obj_type

                params = Parameters()
                params.map = {}
                params.map["oids"] = rlist([rlong(o) for o in oids])

                qs = conn.getQueryService()
                return [result[0].val for result in qs.projection(hql,params, service_opts)]

            # Calculate remaining possible tag navigations
            # TODO Compare subquery to pass-in performance
            # sub_hql = "select link.parent.id from ImageAnnotationLink link " \
            #        "where link.child.id in (:oids) " \
            #        "group by link.parent.id " \
            #        "having count (link.parent) = %s" % len(selected_tags)

            # hql = "select distinct link.child.id from ImageAnnotationLink link " \
            #    "where link.parent.id in (%s)" % sub_hql

            if image_ids:
                remaining.update(getAnnotationsForObjects('Image', image_ids))
            if dataset_ids:
                remaining.update(getAnnotationsForObjects('Dataset', dataset_ids))
            if project_ids:
                remaining.update(getAnnotationsForObjects('Project', project_ids))

            end = time.time()
            logger.info('Tag Query Times. Preview: %ss, Remaining: %ss, Total:%ss' % ((middle-start),(end-middle),(end-start)))

        # Return the navigation data and the html preview for display
        # return {"navdata": list(remaining), "html": html_response}
        return HttpResponse(json.dumps({"navdata": list(remaining),
                                        "preview": preview,
                                        "project_count": project_count,
                                        "dataset_count": dataset_count,
                                        "image_count": image_count,
                                        "html": html_response}),
                            content_type="application/json")

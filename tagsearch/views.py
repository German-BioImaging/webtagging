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

from omeroweb.webclient.controller.container import BaseContainer as BC

class BaseContainer(BC):
    # Also set tags when setting container hierarchy
    def listContainerHierarchy(self, eid=None):
        super(BaseContainer, self).listContainerHierarchy(eid)
        super(BaseContainer, self).loadTags(eid)

    # def listDatasetContents(self, did, eid=None, page=None, load_pixels=False):
    #     super(BaseContainer, self).listImagesInDataset(did, eid, page,
    #                                                    load_pixels)

    #     im_list = self.containers['images']
        
    #     # Get any tags that could be applicable to these images
    #     im_ids = [x.id for x in im_list]
    #     qs = self.conn.getQueryService()

    #     hql = "select distinct link.child from ImageAnnotationLink link " \
    #           "where link.parent.id in (:oids)"

    #     params = Parameters()
    #     params.map = {}
        
    #     params.map["oids"] = rlist([rlong(o) for o in set(im_ids)])

    #     self.tags = list(qs.findAllByQuery(hql, params))
    #     # TODO For now I have ignored tag ownership. Also needs to be added
    #     # back in, in the container_subtree template
    #     # for tag in self.tags:
    #         # print('owner id:', tag.details.getOwner().id.val)

    #     self.tags.sort(key=lambda x: x.textValue.val and x.textValue.val.lower())
    #     self.t_size = len(self.tags)

    #     # TODO Handle paging with some combination of images and tags
    #     # if page is not None:
    #     #     self.paging = self.doPaging(page, len(im_list), self.c_size)


import logging

# helper method
def getIntOrDefault(request, name, default):
    try:
        index = int(request.REQUEST.get(name, default))
    except ValueError:
        index = 0
    return index


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
    tags.update(get_tags('Dataset'))
    tags.update(get_tags('Project'))

    def get_projects_and_datasets():

        # Get all the projects and datasets. Can not rely on just
        # ProjectDatasetLink because it is possible for projects to have no
        # datasets and for datasets not to have any project parent

        pd = {}

        # Projects
        hql = "select project.id, project.name from Project project"

        projects = qs.projection(hql, params, service_opts)


        for project in projects:
            pd[project[0].val] = {'project': (project[0].val, project[1].val)}

        # Datasets
        # Also gets parent projects for any datasets that have them
        hql = "select dataset.id, dataset.name, link.parent.id " \
              "from Dataset dataset " \
              "left outer join dataset.projectLinks link"


        datasets = qs.projection(hql, params, service_opts)
        for dataset in datasets:
            d = (dataset[0].val, dataset[1].val)
            # If this dataset has a parent project then attach it to it
            if dataset[2]:
                pd[dataset[2].val].setdefault('datasets', []).append(d)
            # if not, then it has no parent so make a separate list
            else:
                pd.setdefault('datasets', []).append(d)

        pd = pd.values()
        return pd




    # print(get_projects_and_datasets())

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
                    manager['containers']['images'] = images

                if dataset_ids:
                    datasets = conn.getObjects('Dataset', ids = dataset_ids)
                    manager['containers']['datasets'] = datasets

                if project_ids:
                    projects = conn.getObjects('Project', ids = project_ids)
                    manager['containers']['projects'] = projects

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



###########################################################################
@login_required()
@render_response()
def load_template(request, menu, conn=None, url=None, **kwargs):
    """
    This view handles most of the top-level pages, as specified by 'menu' E.g. userdata, usertags, history, search etc.
    Query string 'path' that specifies an object to display in the data tree is parsed.
    We also prepare the list of users in the current group, for the switch-user form. Change-group form is also prepared.
    """
    request.session.modified = True

    if menu == 'userdata':
        template = "tagsearch/containers.html"
    elif menu == 'usertags':
        template = "webclient/data/container_tags.html"
    else:
        template = "webclient/%s/%s.html" % (menu,menu)

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
    url = reverse(viewname="load_template", args=[menu])

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

    context = {'init':init, 'myGroups':myGroups, 'new_container_form':new_container_form, 'global_search_form':global_search_form}
    context['groups'] = myGroups
    context['active_group'] = conn.getObject("ExperimenterGroup", long(active_group))
    for g in context['groups']:
        g.groupSummary()    # load leaders / members
    context['active_user'] = conn.getObject("Experimenter", long(user_id))

    context['isLeader'] = conn.isLeader()
    context['current_url'] = url
    context['template'] = template

    return context


@login_required(setGroupContext=True)
@render_response()
def load_data(request, o1_type=None, o1_id=None, o2_type=None, o2_id=None, o3_type=None, o3_id=None, conn=None, **kwargs):
    """
    This loads data for the tree, via AJAX calls.
    The template is specified by query string. E.g. icon, table, tree.
    By default this loads Projects and Datasets.
    E.g. /load_data?view=tree provides data for the tree as <li>.
    """
    # get page
    page = getIntOrDefault(request, 'page', 1)
    print('page', page)

    # get view
    view = str(request.REQUEST.get('view', None))
    print('view', view)

    # get index of the plate
    index = getIntOrDefault(request, 'index', 0)

    # prepare data. E.g. kw = {}  or  {'dataset': 301L}  or  {'project': 151L, 'dataset': 301L}
    kw = dict()
    if o1_type is not None:
        if o1_id is not None and o1_id > 0:
            kw[str(o1_type)] = long(o1_id)
        else:
            kw[str(o1_type)] = bool(o1_id)
    if o2_type is not None and o2_id > 0:
        kw[str(o2_type)] = long(o2_id)
    if o3_type is not None and o3_id > 0:
        kw[str(o3_type)] = long(o3_id)

    print('kw', kw)
    try:
        manager= BaseContainer(conn, **kw)
    except AttributeError, x:
        return handlerInternalError(request, x)

    # prepare forms
    filter_user_id = request.session.get('user_id')
    form_well_index = None

    context = {'manager':manager, 'form_well_index':form_well_index, 'index':index}

    # load data & template
    template = None
    if kw.has_key('orphaned'):
        manager.listOrphanedImages(filter_user_id, page)
        if view =='icon':
            template = "webclient/data/containers_icon.html"
        else:
            template = "tagsearch/container_subtree.html"
    elif len(kw.keys()) > 0 :
        if kw.has_key('dataset'):
            load_pixels = (view == 'icon')  # we need the sizeX and sizeY for these
            filter_user_id = None           # Show images belonging to all users
            # List images and relevant tags in dataset
            # manager.listDatasetContents(kw.get('dataset'), filter_user_id, page, load_pixels=load_pixels)
            manager.listImagesInDataset(kw.get('dataset'), filter_user_id, page, load_pixels=load_pixels)
            if view =='icon':
                template = "webclient/data/containers_icon.html"
            else:
                template = "tagsearch/container_subtree.html"
        elif kw.has_key('plate') or kw.has_key('acquisition'):
            if view == 'tree':  # Only used when pasting Plate into Screen - load Acquisition in tree
                template = "tagsearch/container_subtree.html"
            else:
                fields = manager.getNumberOfFields()
                if fields is not None:
                    form_well_index = WellIndexForm(initial={'index':index, 'range':fields})
                    if index == 0:
                        index = fields[0]
                show = request.REQUEST.get('show', None)
                if show is not None:
                    select_wells = [w.split("-")[1] for w in show.split("|") if w.startswith("well-")]
                    context['select_wells'] = ",".join(select_wells)
                context['baseurl'] = reverse('webgateway').rstrip('/')
                context['form_well_index'] = form_well_index
                template = "webclient/data/plate.html"

    # Initial view
    else:
        manager.listContainerHierarchy(filter_user_id)
        if view =='tree':
            template = "tagsearch/containers_tree.html"
        elif view =='icon':
            template = "webclient/data/containers_icon.html"
        else:
            template = "tagsearch/containers.html"

    context['template_view'] = view
    context['isLeader'] = conn.isLeader()
    context['template'] = template
    return context

@login_required(setGroupContext=True)
# @render_response()
def tagsearch_images(request, conn=None, **kwargs):
    """
    This updates the list of tags and images based on the navigation criteria
    """
    if request.method == "POST":
        print('body', request.body)
        json_data = json.loads(request.body)
        tags = [long(x) for x in json_data['tags']]

        # TODO Handle no tags?
        # TODO Handle impossible tag combinations?

        tags = set(tags)
        # validate experimenter is in the active group
        active_group = request.session.get('active_group') or \
                       conn.getEventContext().groupId

        qs = conn.getQueryService()
        service_opts = conn.SERVICE_OPTS.copy()
        service_opts.setOmeroGroup(active_group)

        # Get the image ids that match these tags
        # Also need all the datasets it is a member of and all the projects
        # those datasets are a member of

        # subquery gets a list of relevant images
        # main query then gets the image id, its datasets and projects
        hql = "select image.id, dlink.parent.id, plink.parent.id " \
              "from Image image " \
              "left outer join image.datasetLinks dlink " \
              "left outer join dlink.parent.projectLinks plink " \
              "where image.id in " \
              "(select link.parent.id " \
              "from ImageAnnotationLink link " \
              "where link.child.id in (:oids) " \
              "group by link.parent.id " \
              "having count (distinct link.child) = %s)" % (len(tags))

        params = Parameters()
        params.map = {}
        params.map["oids"] = rlist([rlong(o) for o in tags])

        # TODO optimize this if we don't need the
        # [image_id, dataset_id, project_id] representation
        ids = [(x[0].getValue(), x[1].getValue(), x[2].getValue()) for x in qs.projection(hql,params,service_opts)]
        image_ids = list(set([ x[0] for x in ids ]))
        dataset_ids = list(set([ x[1] for x in ids ]))
        project_ids = list(set([ x[2] for x in ids ]))
        print('image_ids', image_ids)
        print('dataset_ids', dataset_ids)
        print('project_ids', project_ids)

        # TODO Do this for Project/Dataset tags as well.
        hql = "select distinct link.child.id from ImageAnnotationLink link " \
              "where link.parent.id in (:oids)"

        params = Parameters()
        params.map = {}
        params.map["oids"] = rlist([rlong(o) for o in image_ids])

        tag_ids = [x[0].getValue() for x in qs.projection(hql,params,service_opts)]

        return HttpResponse(json.dumps({"images": image_ids,
                                        "datasets": dataset_ids,
                                        "projects": project_ids,
                                        "tags": tag_ids}),
                            content_type="application/json")




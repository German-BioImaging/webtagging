from __future__ import absolute_import
from builtins import map, str
from copy import deepcopy
import json
import logging
from django.http import (
    HttpResponse,
    HttpResponseNotAllowed,
    HttpResponseBadRequest,
    JsonResponse,
)
from omeroweb.webclient.decorators import login_required
import omero
from omero.rtypes import rstring, unwrap
from omeroweb.webclient import tree
from .utils import createTagAnnotationsLinks

logger = logging.getLogger(__name__)


@login_required(setGroupContext=True)
def process_update(request, conn=None, **kwargs):

    if not request.POST:
        return HttpResponseNotAllowed("Methods allowed: POST")

    images = json.loads(request.body)

    additions = []
    removals = []

    for image in images:
        image_id = image["imageId"]

        additions.extend(
            [(int(image_id), int(addition),) for addition in image["additions"]]
        )

        removals.extend(
            [(int(image_id), int(removal),) for removal in image["removals"]]
        )

    # TODO Interface for createTagAnnotationsLinks is a bit nasty, but go
    # along with it for now
    createTagAnnotationsLinks(conn, additions, removals)

    return HttpResponse("")


@login_required(setGroupContext=True)
def create_tag(request, conn=None, **kwargs):
    """
    Creates a Tag from POST data.
    """

    if not request.POST:
        return HttpResponseNotAllowed("Methods allowed: POST")

    tag = json.loads(request.body)

    tag_value = tag["value"]
    tag_description = tag["description"]

    tag = omero.model.TagAnnotationI()
    tag.textValue = rstring(str(tag_value))
    if tag_description is not None:
        tag.description = rstring(str(tag_description))

    tag = conn.getUpdateService().saveAndReturnObject(tag, conn.SERVICE_OPTS)

    params = omero.sys.ParametersI()
    service_opts = deepcopy(conn.SERVICE_OPTS)

    qs = conn.getQueryService()

    q = """
        select new map(tag.id as id,
               tag.textValue as textValue,
               tag.description as description,
               tag.details.owner.id as ownerId,
               tag as tag_details_permissions,
               tag.ns as ns,
               (select count(aalink2)
                from AnnotationAnnotationLink aalink2
                where aalink2.child.class=TagAnnotation
                and aalink2.parent.id=tag.id) as childCount)
        from TagAnnotation tag
        where tag.id = :tid
        """

    params.addLong("tid", tag.id)

    e = qs.projection(q, params, service_opts)[0]
    e = unwrap(e)
    e = [
        e[0]["id"],
        e[0]["textValue"],
        e[0]["description"],
        e[0]["ownerId"],
        e[0]["tag_details_permissions"],
        e[0]["ns"],
        e[0]["childCount"],
    ]

    tag = tree._marshal_tag(conn, e)

    return JsonResponse(tag)


def _marshal_image(conn, row, tags_on_images):
    image = tree._marshal_image(conn, row[0:5])
    image["clientPath"] = unwrap(row[5])
    image["tags"] = tags_on_images.get(image["id"]) or []
    return image


@login_required(setGroupContext=True)
def get_image_detail_and_tags(request, conn=None, **kwargs):
    # According to REST, this should be a GET, but because of the amount of
    # data being submitted, this is problematic
    if not request.POST:
        return HttpResponseNotAllowed("Methods allowed: POST")

    image_ids = request.POST.getlist("imageIds[]")

    if not image_ids:
        return HttpResponseBadRequest("Image IDs required")

    image_ids = list(map(int, image_ids))

    group_id = request.session.get("active_group")
    if group_id is None:
        group_id = conn.getEventContext().groupId

    # All the tags available to the user
    tags = tree.marshal_tags(conn, group_id=group_id)

    # Details about the images specified
    params = omero.sys.ParametersI()
    service_opts = deepcopy(conn.SERVICE_OPTS)

    # Set the desired group context
    service_opts.setOmeroGroup(group_id)

    params.addLongs("iids", image_ids)

    qs = conn.getQueryService()

    # Get the tags that are applied to individual images
    q = """
        SELECT DISTINCT itlink.parent.id, itlink.child.id
        FROM ImageAnnotationLink itlink
        WHERE itlink.child.class=TagAnnotation
        AND itlink.parent.id IN (:iids)
        """

    tags_on_images = {}
    for e in qs.projection(q, params, service_opts):
        tags_on_images.setdefault(unwrap(e[0]), []).append(unwrap(e[1]))

    # Get the images' details
    q = """
        SELECT new map(image.id AS id,
               image.name AS name,
               image.details.owner.id AS ownerId,
               image AS image_details_permissions,
               image.fileset.id AS filesetId,
               filesetentry.clientPath AS clientPath)
        FROM Image image
        JOIN image.fileset fileset
        JOIN fileset.usedFiles filesetentry
        WHERE index(filesetentry) = 0
        AND image.id IN (:iids)
        ORDER BY lower(image.name), image.id
        """

    images = []

    for e in qs.projection(q, params, service_opts):
        e = unwrap(e)[0]
        d = [
            e["id"],
            e["name"],
            e["ownerId"],
            e["image_details_permissions"],
            e["filesetId"],
            e["clientPath"],
        ]
        images.append(_marshal_image(conn, d, tags_on_images))

    # Get the users from this group for reference
    users = tree.marshal_experimenters(conn, group_id=group_id, page=None)

    return JsonResponse({"tags": tags, "images": images, "users": users})

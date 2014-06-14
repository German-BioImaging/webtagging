#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2008-2014 University of Dundee & Open Microscopy Environment.
# All rights reserved.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

''' Helper functions for views that handle object trees '''

from omero.rtypes import rlong, rlist, rstring
from omeroweb.webclient.tree import *

def marshal_tag(conn, row):
    ''' Given a TagAnnotation row (list) marshals it into a dictionary.  Order
        and type of columns in row is:
          * id (rlong)
          * textValue (rstring)
          * details.owner.id (rlong)
          * details.permissions (dict)

        @param conn OMERO gateway.
        @type conn L{omero.gateway.BlitzGateway}
        @param row The TagAnnotation row to marshal
        @type row L{list}
    '''
    tag_id, textValue, owner_id, permissions = row
    tag = dict()
    tag['id'] = tag_id.val
    tag['textValue'] = textValue.val
    tag['isOwned'] = owner_id.val == conn.getUserId()
    tag['permsCss'] = parse_permissions_css(permissions, owner_id.val, conn)
    return tag

# Marshall all tags for the user
def marshal_tags(conn, experimenter_id):
    ''' Marshal tags for a given user.

          @param conn OMERO gateway.
          @type conn L{omero.gateway.BlitzGateway}
          @param experimenter_id The Experimenter (user) ID to marshal
          TagAnnotations for or `None` if we are not to filter by a specific
          user.
          @type experimenter_id L{long}
    '''
    tags = []
    params = omero.sys.ParametersI()
    where_clause = ''
    if experimenter_id is not None:
        params.addId(experimenter_id)
        where_clause = 'and tag.details.owner.id = :id'
    qs = conn.getQueryService()

    q = """
        select tag.id,
               tag.textValue,
               tag.details.owner.id,
               tag.details.permissions
        from TagAnnotation tag
        where tag.ns is null
        %s
        order by lower(tag.textValue)
        """ % (where_clause)

    for e in qs.projection(q, params, conn.SERVICE_OPTS):
        tags.append(marshal_tag(conn, e[0:4]))
    return tags

def marshal_image(conn, row, row_pixels = None, filtered = False,
                  tag_filter_count=0):
    ''' Given an Image row (list) marshals it into a dictionary.  Order
        and type of columns in row is:
          * id (rlong)
          * name (rstring)
          * details.owner.id (rlong)
          * details.permissions (dict)
          * fileset_id (rlong)

        @param conn OMERO gateway.
        @type conn L{omero.gateway.BlitzGateway}
        @param row The Image row to marshal
        @type row L{list}
    '''
    image_id, name, owner_id, permissions, fileset_id = row
    image = dict()
    image['id'] = image_id.val
    image['name'] = name.val
    image['isOwned'] = owner_id.val == conn.getUserId()
    image['permsCss'] = parse_permissions_css(permissions, owner_id.val, conn)
    image['filesetId'] = fileset_id.val
    if row_pixels:
        sizeX, sizeY, sizeZ = row_pixels
        image['sizeX'] = sizeX.val
        image['sizeY'] = sizeY.val
        image['sizeZ'] = sizeZ.val
    if filtered:
        image['isFiltered'] = filtered.val != tag_filter_count

    return image

def marshal_images(conn, experimenter_id=None, dataset_id=None,
                   tag_filter=None, load_pixels=False):
    ''' Marshal images for a given user, possibly filtered by dataset
    '''
    images = []
    params = omero.sys.ParametersI()

    qs = conn.getQueryService()

    # select image.name, pix.sizeX, pix.sizeY, pix.sizeZ from Image image join image.pixels pix
    q = """
        select image.id,
               image.name,
               image.details.owner.id,
               image.details.permissions,
               image.fileset.id
        """

    if load_pixels:
        q += """
             , pix.sizeX,
             pix.sizeY,
             pix.sizeZ
             """

    if tag_filter:
        params.add('tids', rlist([rlong(x) for x in tag_filter]))
        q += """
             , (select count(distinct link.child)
              from ImageAnnotationLink link
              where link.parent.id = image.id
              and link.child.id in (:tids)
             )
             """
    
    q += 'from Image image '

    if load_pixels:
        q += 'join image.pixels pix '

    where_clause = ''
    if dataset_id:
        params.add('did', rlong(dataset_id))
        where_clause = 'join image.datasetLinks dlink ' \
                       'where dlink.parent.id = :did '

    if experimenter_id:
        params.addId(experimenter_id)
        if where_clause == '':
            where_clause += 'where '
        else:
            where_clause += 'and '
        where_clause += 'image.details.owner.id = :id '

    q += where_clause

    for e in qs.projection(q, params, conn.SERVICE_OPTS):
        kwargs = {'conn':conn, 'row':e[0:5]}
        if load_pixels:
            kwargs['row_pixels'] = e[5:8]

        if tag_filter:
            if load_pixels:
                kwargs['filtered'] = e[8]
            else:
                kwargs['filtered'] = e[5]
            kwargs['tag_filter_count'] = len(tag_filter)

        images.append(marshal_image(**kwargs))

    return images


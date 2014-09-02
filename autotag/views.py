import itertools

from django.http import HttpResponse
from django.shortcuts import render

from omeroweb.webclient.decorators import login_required, render_response

import omero
from omero.model import TagAnnotationI
from omero.rtypes import rstring, rlong

from utils import parse_path, createTagAnnotationsLinks, BlitzSet

from urlparse import parse_qsl

import json
import logging

logger = logging.getLogger(__name__)

class Token(object):
    """
    Token type to enable encapsulation of other token related data.
    Can be used as a dictionary key as this is hashable
    """

    def __init__(self, value, tokentype):
        self.value = value
        self.tokentype = tokentype
        self.tags = BlitzSet([])
        self.rows = set([])

    def __hash__(self):
        return hash(self.value)

    def __eq__(self, other):
        return other.value == self.value

    def __repr__(self):
        return self.value

    def add_tags(self, tags):
        self.tags.update(tags)

    def add_row(self, row):
        self.rows.add(row)

    def set_tokentype(self, tokentype):
        """
        Allow the tokentype to be overriden should the type of the token
        be upgraded. This may happen when a token is found in a path of one
        file, then subsequently in the file in another.
        """
        self.tokentype = tokentype


class TableHeader(object):
    def __init__(self, parent):
        self.parent = parent


class TableHeaderToken(TableHeader):
    def __init__(self, parent, token):
        super(TableHeaderToken, self).__init__(parent)
        self.token = token      # Token value

    def is_token_header(self):
        """
        Is this object a token_header

        This is for the benefit of django templates
        """

        return True

    def is_enabled(self):
        """
        A token header is disabled if there is not a 1-1 mapping
        between token and tag. 0 or 2+ tags results in a disabled column
        1 tag exactly enables it
        """

        return len(self.token.tags) == 1

    def single_tag(self):
        """
        If this token header is enabled, then this returns the single tag
        that corresponds to it. Returns nothing if the column is disabled
        """
        if self.is_enabled():
            return iter(self.token.tags).next()

    def is_checked(self):
        # Iterate over this whole column to see if they are all checked
        for row in self.parent.rows:
            # If the row doesn't have this token present - unchecked
            if self.token not in row.tokens:
                return False
            # If the row doesn't have the single_tag present - unchecked
            if self.single_tag() not in row.tags:
                return False
        # Otherwise checked
        return True


class TableHeaderTag(TableHeader):
    def __init__(self, parent, tag):
        super(TableHeaderTag, self).__init__(parent)
        self.tag = tag          # Tag Annotation

    def is_tag_header(self):
        """
        Is this object a tag_header

        This is for the benefit of django templates
        """

        return True

    def is_checked(self):
        # Iterate over this whole column to see if they are all checked
        for row in self.parent.rows:
            # If the row doesn't have the single_tag present - unchecked
            if self.tag not in row.tags:
                return False
        # Otherwise checked
        return True

class TableCellToken(TableHeader):
    def __init__(self, parent, token):
        super(TableCellToken, self).__init__(parent)
        self.token = token

    def is_token_cell(self):
        """
        Is this object a token_cell

        This is for the benefit of django templates
        """

        return True

    def is_checked(self):
        """
        If this token is present in this row or the tag is applied
        """
        if self.token in self.parent.tokens:
            return True
        if self.is_tagged():
            return True
        return False

    def is_enabled(self):
        """
        A token header is disabled if there is not a 1-1 mapping
        between token and tag. 0 or 2+ tags results in a disabled column
        1 tag exactly enables it
        """
        return len(self.token.tags) == 1

    def single_tag(self):
        """
        If this token header is enabled, then this returns the single tag
        that corresponds to it. Returns nothing if the column is disabled
        """
        if self.is_enabled():
            return iter(self.token.tags).next()

    def is_tagged(self):
        """
        If this column is enabled, then it might have the tag from the
        token->tag mapping applied
        """
        if self.is_enabled():
            return self.single_tag() in self.parent.tags


class TableCellTag(TableHeader):
    def __init__(self, parent, tag):
        super(TableCellTag, self).__init__(parent)
        self.tag = tag

    def is_tag_cell(self):
        """
        Is this object a tag_cell

        This is for the benefit of django templates
        """
        return True

    def is_checked(self):
        """
        If this tag is applied
        """
        return self.is_tagged()

    def is_tagged(self):
        """
        If this column is enabled, then it might have the tag from the
        token->tag mapping applied
        """
        return self.tag in self.parent.tags


class TableRow(object):
    """
    Row representing an image along which will, on-demand, return the 
    token and tag information associated with that image
    """

    def __init__(self, parent, image):
        self.parent = parent    # Parent table for referencing 'all' variables
        self.image = image      # Details of the image
        self.tokens = set([])   # The tokens present in this image name
        self.tags = []          # The tags present on this image
        self.client_path = None
        # self.perms = []         # Users permissions on this image

    def get_name(self):
        return self.image.getName()

    def get_client_path(self):
        if self.client_path:
            return self.client_path
        else:
            return self.get_name()

    def set_client_path(self, client_path):
        self.client_path = client_path

    def get_id(self):
        return self.image.getId()

    def get_cells(self):
        """
        List of tokens in the same order as the header
        """
        # Use parent's list of tokens to create the order
        for token in self.parent.all_tokens:
            yield TableCellToken(self, token)

        for tag in self.parent.get_unmatched_tags():
            yield TableCellTag(self, tag)

    def can_annotate(self):
        return self.image.canAnnotate()

    def add_token(self, token):
        """
        Add token to this image
        """
        self.tokens.add(token)  # Add token as present in the row
        token.add_row(self)     # Automatically add back-reference to this row
        # TODO Should this not be automatically updating all_tokens in
        # table_data???

    def add_tags(self, tags):
        """
        Add tags that are present on this image
        """
        self.tags.extend(tags)              # Add tag as present in the row
        self.parent.all_tags.update(tags)   # Automatically update all_tags

    def __hash__(self):
        return hash(self.image.getId())

    def __eq__(self, other):
        return other.image.getId() == self.image.getId()

    def generate_state(self):
        """
        Generate a data object for conversion to JSON
        """
        state_image = {'name': self.get_name()}

        # Add all the tokens if there are any
        if self.parent.all_tokens:
            state_image['tokens'] = {}
            for token in self.parent.all_tokens:
                state_image['tokens'][token.value] = {
                    'name': token.value,
                    'autoselect': token in self.tokens
                }

                # If there is just the one tag mapping
                if len(token.tags) == 1:
                    # Get the tag that is mapped to
                    tag = iter(token.tags).next()
                    # Check if it is applied to this row
                    if tag in self.tags:
                        state_image['tokens'][token.value]['autoselect'] = True

                if token.tags:
                    state_image['tokens'][token.value]['tags'] = [
                        tag.getId() for tag in token.tags
                    ]

        return state_image


class TableData(object):
    """
    Top level data object representing the full table of data to be displayed
    Generates the data on-demand to return headers and rows
    """

    def __init__(self):
        self.all_tags = BlitzSet([])    # Set of all tags
        self.all_tokens = []            # List of all tokens

        self.matched_tags = BlitzSet([])    # Set of matched tags for quickref

        self.rows = []       # List of rows (images)


    def get_rows(self):
        """
        Get the rows representing images and token/tag data

        Also causes rows to be sorted before returning.
        """

        self.sort_rows()
        return self.rows

    def add_image(self, image):
        """
        Add a row for the specified image
        """

        # Create the row with the supplied image
        row = TableRow(self, image)

        # Add the row
        self.rows.append(row)

        # Return the row in case local manipulation is desired
        return row

    def set_tokens(self, tokens):
        """
        Set and sort the full list of tokens
        """

        self.all_tokens.extend(tokens)
        # tokentype ordering should be: path > file > extension. This happens
        # to be reverse alphabetical. If tokentypes get more complicated then
        # this will need to be changed
        self.all_tokens.sort(
            key = lambda token : (token.tokentype, token.value),
            reverse = True
        )

    def remove_token(self, token):
        """
        Remove token from all_tokens and from any rows in which it was used.

        This is normally used when a token has been added on the condition
        that it already has a preexisting tag. E.g. '5' is a valid token
        only if there is a tag with that value already. If it is not valid
        then this method is employed to remove the '5' token
        """

        # Remove from any rows where the token was used
        for row in token.rows:
            row.tokens.remove(token)
        # Remove from all_tokens
        self.all_tokens.remove(token)

    def get_unmatched_tags(self):
        """
        Get all the unmatched tags from the set of all rows

        Up until this point, unmatched_tags have not been calculated
        or ordered. The first time this is called, calculate and sort
        unmatched_tags. On subsequent calls, return this sorted list.
        """

        if not hasattr(self, 'unmatched_tags'):
            self.unmatched_tags = list(self.all_tags - self.matched_tags)
        return self.unmatched_tags

    def headers(self):
        """
        Return the header row

        The header row contains an ordered list of tokens/unmatched tags
        """
        
        # Item per token
        for token in self.all_tokens:
            yield TableHeaderToken(self, token)

        # Item per unmatched tag
        for tag in self.get_unmatched_tags():
            yield TableHeaderTag(self, tag)


    def sort_rows(self):
        """
        Sort rows based upon the image name the row represents
        """

        self.rows.sort(
            key=lambda row: row.image.getName().lower()
        )

    def generate_state(self):
        """
        Generate a data object for conversion to JSON

        {
            imageid: {
                'name':imagename,
                'tokens': {
                    tokenname: {
                        'name': tokenname,
                        'autoselect': autoselect,
                        'tags': [tagids]

                        ]
                    }
                }
            }
        }

        """

        state_details = dict(
            (row.get_id(), row.generate_state()) for
            row in self.rows
        )

        return state_details


def index(request):
    """
    Just a place-holder, base for creating urls etc
    """

    return HttpResponse("Welcome to webtagging")


@login_required(setGroupContext=True)
@render_response()
def auto_tag(request, datasetId=None, conn=None, **kwargs):
    """
    List all the images in a table, with their names tokenised to create 
    suggestions for new tags.
    Indicate where these match existing tags etc.
    """
    import time
    start = time.time()

    # TODO: handle list of Image IDs. Currently we ONLY support Dataset
    if datasetId is not None:
        dataset = conn.getObject("Dataset", datasetId)
        images = list( dataset.listChildren() )
        images.sort(key=lambda img: img.getName().lower())

    ignoreFirstFileToken = bool(request.GET.get('ignoreFirstFileToken', False))
    ignoreLastFileToken = bool(request.GET.get('ignoreLastFileToken', False))

    table_data = build_table_data(
        conn,
        images,
        ignoreFirstFileToken=ignoreFirstFileToken,
        ignoreLastFileToken=ignoreLastFileToken
    )

    # We only need to return a dict - the @render_response() decorator does
    # the rest...
    context = {'template': 'autotag/tags_from_names.html'}
    context['table_data'] = table_data
    context['imageStates'] = json.dumps(table_data.generate_state())
    context['ignoreFirstFileToken'] = ignoreFirstFileToken
    context['ignoreLastFileToken'] = ignoreLastFileToken

    end = time.time()
    logger.info('AutoTag Assemble Data Time: %ss' % (end-start))
    return context


def build_table_data(conn, images, ignoreFirstFileToken=False,
                     ignoreLastFileToken=False):
    """
    We need to build tagging table data when the page originally loads 
    """

    def listTags(image):
        """ This should be in the BlitzGateway! """
        return [a for a in image.listAnnotations() if a.__class__.__name__ ==
                "TagAnnotationWrapper"]

    # New all_table data
    table_data = TableData()

    # First go through all images, getting all the tokens

    # Complete list of Tokens. If a Token already exists it is read from here
    # instead of being recreated. If necessary, it has its tokentype overriden
    # if the type being added has a higher degree of precedence than before
    #TODO If we ever need this later, it could be put straight into TableData
    # in place of the all_tokens list that is currently stored there
    all_tokens = {}

    # Process the images to extract tokens only
    for image in images:

        # Create the TableRow for this image
        row = table_data.add_image(image)
        # row = TableRow(table_data, image)

        # Use the full client import path if possible
        name = image.getClientPath().strip()
        # If not possible (OMERO 4.4.x), just use the name
        if len(name) > 0:
            # Set the client_path so this can be used in in the rendering
            # If this isn't set, then the image name gets used instead
            row.set_client_path(name)
        else:
            name = image.getName()
 
        pt, ft, et = parse_path(name)
        
        # Do discards
        #TODO Incredibly primitive, replace with much, much smarter discarding
        # system
        if (ignoreFirstFileToken):
            ft.pop(0)
        if (ignoreLastFileToken):
            ft.pop()


        # Convert tokens to Tokens
        # TODO Refactor these into a function

        # Process path tokens (Lowest priorty so never override)
        for t in pt:
            # Skip zero length tokens
            if len(t) == 0:
                continue
            if t in all_tokens:
                token = all_tokens[t]
            else:
                token = Token(t, 'path')
                all_tokens[t] = token
            row.add_token(token)

        # Process Extension tokens (Middle priority so only override if 
        # current tokentype is 'path')
        for t in et:
            # Skip zero length tokens
            if len(t) == 0:
                continue
            if t in all_tokens:
                token = all_tokens[t]
                if token.tokentype == 'path':
                    token.set_tokentype('ext')
            else:
                token = Token(t, 'ext')
                all_tokens[t] = token
            row.add_token(token)

        # Process file tokens (highest priority so override all)
        for t in ft:
            # Skip zero length tokens
            if len(t) == 0:
                continue
            if t in all_tokens:
                token = all_tokens[t]
                token.set_tokentype('file')
            else:
                token = Token(t, 'file')
                all_tokens[t] = token
            row.add_token(token)

    # Update table_data with the full list of Tokens
    table_data.set_tokens(all_tokens.values())


    # List of all token details: [{name, tokenType, tagList}, ... ]
    # token_details = []

    # Find which tokens match existing Tags
    for token in table_data.all_tokens[:]:

        # Get all tags matching the token
        # TODO Could I reduce this to one query which takes all the tokens?
        tags = list(conn.getObjects(
            "TagAnnotation", 
            attributes={'textValue':token.value})
        )

        # Any tokens that are simply numbers that are not already tags
        if token.value.isdigit() and len(tags) == 0:
            # these need to be removed from the all_list and the rows
            table_data.remove_token(token)
            # Then continue to the next token
            continue

        # Add the matching tags to this token
        token.add_tags(tags)

        # Update the matched_tags in table_data
        table_data.matched_tags.update(tags)
        # TODO Do I need to update the all_tags in table_data??

    # Find the tags that are prexisting on these images
    for row in table_data.rows:
        # Get the tags on this image
        tags = listTags(row.image)

        # Add the tags to this image's row and automatically the all_tags list
        row.add_tags(tags)

    return table_data

@login_required(setGroupContext=True)
@render_response()
def process_update(request, conn=None, **kwargs):
    if request.method == "POST":
        
        tagSelector = request.POST.getlist('tag-selector')
        serverSelectedPost = request.POST.getlist('serverselected')
        checkedPost = request.POST.getlist('imagechecked')

        # Convert the posted data into something more manageable:

        # Mappings between token and tags
        # tokenTags = { tokenName: tagId }
        tokenTags = {}
        for tokenTag in tagSelector:
            tokenName,tagId = tokenTag.rsplit(r'_', 1)
            tokenTags[tokenName] = long(tagId)

        # tokens (with current token->tag mappings) that are already applied
        # serverSelected = { imageId: [tokenName]}
        serverSelected = {}
        server_selected_tag_ids = {}
        for s in serverSelectedPost:
            tag_or_token, imageId, token_name_or_tag_id = s.split(r'_',2)
            if tag_or_token == 'token':
                serverSelected.setdefault(long(imageId), []).append(
                    token_name_or_tag_id
                )
            elif tag_or_token == 'tag':
                server_selected_tag_ids.setdefault(long(imageId), []).append(
                    long(token_name_or_tag_id)
                )

        # tokens that are checked
        # checked = { imageId: [tokenName] }
        checked = {}
        # unmatched tags that are checked
        # checked_tag_ids = { imageId: [tagId]}
        checked_tag_ids = {}
        for c in checkedPost:
            tag_or_token, imageId, token_name_or_tag_id = c.split(r'_', 2)
            if tag_or_token == 'token':
                # Ignore submissions from unmapped tokens
                if token_name_or_tag_id in tokenTags:
                    checked.setdefault(long(imageId), []).append(
                        token_name_or_tag_id
                    )
            elif tag_or_token == 'tag':
                checked_tag_ids.setdefault(long(imageId), []).append(
                    long(token_name_or_tag_id)
                )

        # Get the list of images that may require operations as they have some
        # selections (could be being removed) or checks (could be being added)
        imageIds = list(set(serverSelected.keys() + checked.keys()))

        # tokenName can be None in these to denote a unmatched tag
        additions = []      # [(imageID, tagId, tokenName)]
        removals = []       # [(imageId, tagId, tokenName)]

        # Create a list of tags to add on images and one to remove tags from
        # images
        for imageId in imageIds:

            # Not every image will have both of these so have to default to
            # empty list
            checkedTokens = []
            selectedTokens = []

            # If there are checked checkboxes for this image
            if imageId in checked:
                checkedTokens = checked[imageId]

            # If there are server selected tokens for this image
            if imageId in serverSelected:
                selectedTokens = serverSelected[imageId]

            # Add any tokens (for addition) that are not preexisting
            # (checked - serverSelected)
            additionsTokens = list(set(checkedTokens) - set(selectedTokens))
            # Add any tokens (for removal) that are prexisiting but not
            # checked (serverSelected - checked)
            removalsTokens = list(set(selectedTokens) - set(checkedTokens))

            # Resolve tokenNames to tagIds, but keep tokenNames as the client
            # needs these back to update the table
            for tokenName in additionsTokens:
                # Resolve tokenName to a tagId
                tagId = tokenTags[tokenName]
                additions.append((imageId, tagId, tokenName))

            for tokenName in removalsTokens:
                # Resolve tokenName to a tagId
                tagId = tokenTags[tokenName]
                removals.append((imageId, tagId, tokenName))

            # Now do the same for the tag fields

            # Not every image will have both of these so have to default to
            # empty list
            checked_tags = []
            selected_tags = []

            # if there are checked unmapped tag checkboxes for this image
            if imageId in checked_tag_ids:
                checked_tags = checked_tag_ids[imageId]

            # If there are server selected unmapped tags for this image
            if imageId in server_selected_tag_ids:
                selected_tags = server_selected_tag_ids[imageId]

            # Add any tags (for addition) that are not prexisting
            additions_tags = list(set(checked_tags) - set(selected_tags))
            # Add any tags (for removal) that are prexisting, but not checked
            removals_tags = list(set(selected_tags) - set(checked_tags))

            for tag_id in additions_tags:
                additions.append((imageId, tag_id, None))

            for tag_id in removals_tags:
                removals.append((imageId, tag_id, None))
                
        # TODO Problem is that unmatched tags are being marked for addition
        # even if they are already tagged

        #TODO Return success/failure of each addition/removal
        #TODO The success/failure need not contain the tagId like these
        # additions/removals do, html will be indexing so will need to change
        # there also.
        createTagAnnotationsLinks(conn, additions, removals)
    
    successfulUpdates = {'additions': additions, 'removals': removals}

    # We only need to return a dict - the @render_response() decorator does
    # the rest...
    return successfulUpdates


@login_required(setGroupContext=True)
@render_response()
def list_tags(request, conn=None, **kwargs):
    """
    List all tags in the current group
    """
    current_tags = []
    if request.POST:

        current_tags = request.POST.getlist("current_tag_ids[]")
        current_tags = map(long, current_tags)

    tags = []
    for t in conn.getObjects("TagAnnotation"):
        if t.id not in current_tags:
            tags.append({
                'id':t.id,
                'name':t.getTextValue(),
                'desc':t.getDescription(),
                'owner':t.getOwnerFullName()
            })

    return {'template': 'autotag/tag_dialog_form.html', 'tags':tags}


@login_required(setGroupContext=True)
@render_response()
def create_tag(request, conn=None, **kwargs):
    """
    Creates a Tag from POST data. "tag_name" & "tag_description"
    """
    if not request.POST:
        return {"error": "need to POST"}

    tag_name = request.POST.get("tag_name")
    tag_desc = request.POST.get("tag_description", None)

    tag = omero.model.TagAnnotationI()
    tag.textValue = rstring(str(tag_name))
    if tag_desc is not None:
        tag.description = rstring(str(tag_desc))

    tag = conn.getUpdateService().saveAndReturnObject(tag, conn.SERVICE_OPTS)
    tag = conn.getObject("TagAnnotation", tag.id.val)

    return {'id':tag.id,
            'name':tag.getTextValue(),
            'desc':tag.getDescription(),
            'owner':tag.getOwnerFullName()}

@login_required(setGroupContext=True)
@render_response()
def get_tag_on_images(request, conn=None, **kwargs):
    """
    Given a TagId and a list of images, determine the tagged status for each
    """

    if not request.POST:
        return {"error": "need to POST"}

    tagId = request.POST.get("tag_id")
    imageIdList = request.POST.getlist("image_ids[]")

    if not tagId or not imageIdList:
        return {"error": "need a tagId and imageId list to process"}

    tagId = long(tagId)
    imageIdList = map(long, imageIdList)

    params = omero.sys.Parameters()
    links = conn.getAnnotationLinks("Image",
                                    parent_ids=imageIdList,
                                    ann_ids=[tagId],
                                    params=params)

    tagOnImages = []
    # Only return imageIds
    for link in links:
        tagOnImages.append(link.parent.id.val)

    return tagOnImages

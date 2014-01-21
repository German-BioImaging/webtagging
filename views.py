from django.http import HttpResponse
from django.shortcuts import render

from omeroweb.webclient.decorators import login_required, render_response

import omero
from omero.model import TagAnnotationI
from omero.rtypes import rstring, rlong

from utils import parse_path, createTagAnnotationsLinks

from urlparse import parse_qsl

import json

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

    # TODO: handle list of Image IDs. Currently we ONLY support Dataset
    if datasetId is not None:
        dataset = conn.getObject("Dataset", datasetId)
        images = list( dataset.listChildren() )
        images.sort(key=lambda img: img.getName().lower())

    ignoreFirstFileToken = bool(request.GET.get('ignoreFirstFileToken', False))
    ignoreLastFileToken = bool(request.GET.get('ignoreLastFileToken', False))

    tokenTags, imageDetails, imageStates = build_table_data(conn, images, ignoreFirstFileToken=ignoreFirstFileToken, ignoreLastFileToken=ignoreLastFileToken)

    # We only need to return a dict - the @render_response() decorator does the rest...
    context = {'template': 'webtagging/tags_from_names.html'}
    context['token_details'] = tokenTags
    context['image_details'] = imageDetails
    context['imageStates'] = json.dumps(imageStates)
    context['ignoreFirstFileToken'] = ignoreFirstFileToken
    context['ignoreLastFileToken'] = ignoreLastFileToken
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

    # Reference Variables
    all_tags = set([])

    # First go through all images, getting all the tokens
    # Each set of tokens must be separate so that they can be distinguished
    pathTokens = []
    fileTokens = []
    extTokens = []
    # Also record which tokens are in which images to avoid reparsing later
    # per-image
    images_tokens = {}

    # Process the images to extract tokens only
    for image in images:
        name = image.getName()
 
        pt, ft, et = parse_path(name)
        
        # Do discards
        #TODO Incredibly primitive, replace with much, much smarter discarding system
        if (ignoreFirstFileToken):
            ft.pop(0)
        if (ignoreLastFileToken):
            ft.pop()

        pathTokens.extend(pt)
        fileTokens.extend(ft)
        extTokens.extend(et)
        images_tokens[image] = set(pt + et + ft)

    # Remove duplicates from each set
    pathTokens = set(pathTokens)
    fileTokens = set(fileTokens)
    extTokens = set(extTokens)
    # Remove duplicates that exist between sets (from path, then extenstion)
    pathTokens = pathTokens - fileTokens
    pathTokens = pathTokens - extTokens
    extTokens = extTokens - fileTokens

    # Convert back to list
    pathTokens = list(pathTokens)
    fileTokens = list(fileTokens)
    extTokens = list(extTokens)

    # Order the lists by name
    pathTokens.sort(key=lambda name: name.lower())
    fileTokens.sort(key=lambda name: name.lower())
    extTokens.sort(key=lambda name: name.lower())

    tokens = {'pathTokens': pathTokens, 'fileTokens': fileTokens,
              'extTokens': extTokens}

    # List of all token details: [{name, tokenType, tagList}, ... ]
    # TODO Not Indexed as it is not used in lookups?
    token_details = []
    # Find which tokens match existing Tags
    for tokenType in ['pathTokens', 'fileTokens','extTokens']:
        for token in tokens[tokenType]:

            # Skip zero length tokens
            if len(token) == 0:
                continue

            # Get all tags matching the token
            # TODO Could I reduce this to one query which takes all the tokens?
            tags = list(conn.getObjects("TagAnnotation",
                                                attributes={'textValue':token}))

            # Skip any tokens that are simply numbers that are not already tags
            if token.isdigit() and len(tags) == 0:
                continue

            # Update the tag reference variable
            all_tags.update(tags)

            # Dictionary storing the token's name and type, plus the
            # corresponding tags (if any)
            token_detail = {'name': token, 'tokenType': tokenType}
            if len(tags) > 0:
                token_detail['tags'] = tags
            token_details.append(token_detail)

    # Populate a variable with details that need to be passed to build the table
    image_details = []

    # Dictionaries of dictionaries of dictionaries was beginning to 
    # get a bit confusing so these helper classes keep things
    # organised.
    class ImageTokenDetail(object):
        def __init__(self, name, tokentype):
            self.name = name
            self.tokentype = tokentype
            self.autoselect = False
            self.applied = False
            self.disabled = False
            self.tags = None

        def set_autoselect(self):
            self.autoselect = True

        def set_applied(self):
            self.applied = True

        def set_disabled(self):
            self.disabled = True

        def set_tags(self, tags):
            self.tags = tags

        def generate_state(self):
            state_token = {'name': self.name,
                           'autoselect': self.autoselect}

            # Add the tag_ids (if there are any)
            if self.tags:
                state_token['tags'] = [tag.getId() for tag in self.tags]

            return state_token


    class ImageDetail(object):
        def __init__(self, image):
            self.image = image
            self.tokens = []

        def add_token(self, token):
            self.tokens.append(token)

        def generate_state(self):
            state_image = {'name': image.getName()}

            # Add the tokens if there are any
            if self.tokens:
                state_image['tokens'] = dict(
                    (token.name, token.generate_state()) for
                     token in self.tokens
                )
                # Pre Python 2.7, dictionary comprehension is not possible
                # state_image['tokens'] = {token.name: token.generate_state() for 
                                         # token in self.tokens}
            return state_image


    # Process the images again using the images_tokens lookup to avoid reparsing
    # all the tokens from the images
    image_details = []
    for image, image_tokens in images_tokens.iteritems():

        # Set the basic details
        image_detail = ImageDetail(image)

        # Which tags are already applied to this image?
        tags = listTags(image)

        # Update the tag reference variable
        all_tags.update(tags)


        # Reference of tags that are on this image
        # indexed by value which is the match for tokens
        tags_on_image = {}
        for tag in tags:
            tags_on_image.setdefault(tag.getValue(),[]).append(tag)

        # Now determine what should be done for every token appearing in this
        # set of results, for this image. Some will be relevant, others will
        # now be, but they have to be included in the results anyway to denote
        # that.
        for token_detail in token_details:
            # Details object of how this token is treated for this image
            # 'name' and 'tokentype' could be looked up in the template, but
            # it is much easier just to include them here.
            image_token_detail = ImageTokenDetail(token_detail['name'],
                                                  token_detail['tokenType'])

            # If the token is present in the image
            if token_detail['name'] in image_tokens:
                # Mark the token for autoselect (Do this even if the token is
                # not matched as a visual aid to the user)
                image_token_detail.set_autoselect()

            # Does this token have a single tag match that is already
            # applied to this image?

            # If there are any any tags associated with this token
            if token_detail['name'] in tags_on_image:
                # If this image has tags and actually exactly 1
                if ('tags' in token_detail and
                        len(token_detail['tags']) == 1 ):
                    # Set the image as having this token (and its one
                    # corresponding tag) applied
                    image_token_detail.set_applied()


                # For the purposes of the state, add the tags that match
                # to this token
                image_token_detail.set_tags(tags_on_image[token_detail['name']])


            # Does this token have a number of matching tags other
            # than 1, then the column is disabled
            # 'disabled' could be looked up in the template, but it is
            # much easier to include it here.
            if 'tags' not in token_detail or len(token_detail['tags']) != 1:
                image_token_detail.set_disabled()

            # Add the populated details about this token for this image
            image_detail.add_token(image_token_detail)

        # Add the populated details about this image to the list
        image_details.append(image_detail)

    # Sort the list of images
    image_details.sort(
        key=lambda image_detail: image_detail.image.getName().lower()
    )

    return token_details, image_details, {image_detail.image.getId():
                                          image_detail.generate_state() for
                                          image_detail in image_details}

@login_required(setGroupContext=True)
@render_response()
def process_update(request, conn=None, **kwargs):
    if request.method == "POST":
        
        tagSelector = request.POST.getlist('tag-selector')
        serverSelectedPost = request.POST.getlist('serverselected')
        checkedPost = request.POST.getlist('imagechecked')

        # Convert the posted data into something more manageable
        # tokenTags = { tokenName: tagId }
        tokenTags = {}
        for tokenTag in tagSelector:
            tokenName,tagId = tokenTag.rsplit(r'_', 1)
            tokenTags[tokenName] = long(tagId)

        # serverSelected = { imageId: [tokenName]}
        serverSelected = {}
        for s in serverSelectedPost:
            imageId,tokenName = s.split(r'_',1)
            serverSelected.setdefault(long(imageId), []).append(tokenName)
        # checked = { imageId: [tokenName] }
        checked = {}
        for c in checkedPost:
            imageId,tokenName = c.split(r'_', 1)
            # Ignore submissions from unmapped tokens
            if tokenName in tokenTags:
                checked.setdefault(long(imageId), []).append(tokenName)

        # Get the list of images that may require operations as they have some selections or checks
        imageIds = list(set(serverSelected.keys() + checked.keys()))

        additions = []  # [(imageID, tagId, tokenName)]
        removals = []   # [(imageId, tagId, tokenName)]
        # Create a list of tags to add on images and one to remove tags from images
        for imageId in imageIds:

            # Not every image will have both of these so have to default to empty list
            checkedTokens = []
            selectedTokens = []

            # If there are checked checkboxes for this image
            if imageId in checked:
                checkedTokens = checked[imageId]

            # If there are server selected tokens for this image
            if imageId in serverSelected:
                selectedTokens = serverSelected[imageId]

            # Add any tokens (for addition) that are not preexisting (checked - serverSelected)
            additionsTokens = list(set(checkedTokens) - set(selectedTokens))
            # Add any tokens (for removal) that are prexisiting but not checked (serverSelected - checked)
            removalsTokens = list(set(selectedTokens) - set(checkedTokens))

            # Resolve tokenNames to tagIds, but keep tokenNames as the client needs these back to update the table
            for tokenName in additionsTokens:
                # Resolve tokenName to a tagId
                tagId = tokenTags[tokenName]
                additions.append((imageId, tagId, tokenName))

            for tokenName in removalsTokens:
                # Resolve tokenName to a tagId
                tagId = tokenTags[tokenName]
                removals.append((imageId, tagId, tokenName))
                
        #TODO Return success/failure of each addition/removal
        #TODO The success/failure need not contain the tagId like these additions/removals do, html will be indexing so will need to change there also.
        createTagAnnotationsLinks(conn, additions, removals)
    
    successfulUpdates = {'additions': additions, 'removals': removals}

    # We only need to return a dict - the @render_response() decorator does the rest...
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
            tags.append({'id':t.id, 'name':t.getTextValue(), 'desc':t.getDescription(), 'owner':t.getOwnerFullName()})

    return {'template': 'webtagging/tag_dialog_form.html', 'tags':tags}


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

    return {'id':tag.id, 'name':tag.getTextValue(), 'desc':tag.getDescription(), 'owner':tag.getOwnerFullName()}

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
    links = conn.getAnnotationLinks("Image", parent_ids=imageIdList, ann_ids=[tagId], params=params)

    tagOnImages = []
    # Only return imageIds
    for link in links:
        tagOnImages.append(link.parent.id.val)

    return tagOnImages

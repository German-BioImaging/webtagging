from django.http import HttpResponse

from omeroweb.webclient.decorators import login_required, render_response

import omero
from omero.model import TagAnnotationI
from omero.rtypes import rstring

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

    tokenTags, imageDetails, imageStates = build_table_data(conn, images)
    # We only need to return a dict - the @render_response() decorator does the rest...
    context = {'template': 'webtagging/tags_from_names.html'}
    context['tokenTags'] = tokenTags
    context['imageDetails'] = imageDetails
    print 'imageStates: ', imageStates
    context['imageStates'] = json.dumps(imageStates)
    return context


def build_table_data(conn, images):
    """
    We need to build tagging table data when the page originally loads AND after form processing
    """

    def listTags(image):
        """ This should be in the BlitzGateway! """
        return [a for a in image.listAnnotations() if a.__class__.__name__ == "TagAnnotationWrapper"]

    # Need to build our table...

    # First go through all images, getting all the tokens
    # Each set of tokens must be separate so that they can be distinguished
    pathTokens = []
    fileTokens = []
    extTokens = []
    # Also record which tokens are in which images to avoid reparsing later per-image
    imagesTokens = {}

    for image in images:
        name = image.getName()
 
        pt, ft, et = parse_path(name)
        pathTokens.extend(pt)
        fileTokens.extend(ft)
        extTokens.extend(et)
        imagesTokens[image] = set(pt + et + ft)

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

    tokens = {'pathTokens' : pathTokens, 'fileTokens' : fileTokens, 'extTokens' : extTokens}

    tokenTags = {}
    # find which tokens match existing Tags
    for tokenType in ['pathTokens', 'fileTokens','extTokens']:
        tt = []
        for token in tokens[tokenType]:

            # Skip zero length tokens
            if len(token) == 0:
                continue

            # Skip (at least for now) tokens that are simply numbers
            if token.isdigit():
                continue

            # Get all tags matching the token
            matchingTags = list(conn.getObjects("TagAnnotation", attributes={'textValue':token}))

            tags = []
            # For each of the matching tags
            for matchingTag in matchingTags:
                # Add dictionary of details
                tags.append({'name':matchingTag.getValue(), 'id':matchingTag.getId(), 'desc':matchingTag.getDescription()})

            tokenTagMap = {'name':token}

            # Assign the matching tags to the token dictionary (only if there are any)
            if len(tags) > 0:
                tokenTagMap['tags'] = tags

            # Add the token with any tag mappings to the list
            tt.append(tokenTagMap)

        tokenTags[tokenType] = tt

    # Populate the images with details
    imageDetails = []
    imageStates = {}

    for image, allTokens in imagesTokens.iteritems():

        # Create mapping of tags that exist already on this image (tagValue : [ids])
        imageTags = {}
        for tag in listTags(image):
            if tag.getValue() in imageTags:
                imageTags[tag.getValue()].append(tag.getId())
            else:
                imageTags[tag.getValue()] = [tag.getId()]

        imageTokens = []
        imageTokenStates = {}
        # For each token that exists (tokens from all images)
        for tokenType in ['pathTokens', 'fileTokens','extTokens']:
            for token in tokenTags[tokenType]:
                imageToken = {'name':token['name']}
                # If the token is present in the image
                if token['name'] in allTokens:
                    # Get the tags (if any) that are relevant
                    if 'tags' in token:
                        tags = token['tags']
                        # If exactly 1 tag exists for this image
                        if len(tags) == 1:
                            # Mark the token as matched
                            imageToken['matched'] = True
                    # Mark the token for autoselect (Do this even if the token is not matched)
                    imageToken['autoselect'] = True

                # Assign token type
                imageToken['tokenType'] = tokenType

                # Add all the matching tags 
                if token['name'] in imageTags:
                    # Add the tagIds that match to this token
                    imageToken['tags'] = imageTags[token['name']]

                    # If there is just the one matching tag for this column, mark the token selected
                    #TODO This can be removed in favor of a simple filter in django ??
                    if len(token['tags']) == 1:
                        imageToken['selected'] = True

                imageTokens.append(imageToken)
                imageTokenStates[token['name']] = imageToken

        imageDetail = {'id':image.getId(), 'name':image.getName(), 'tokens':imageTokens}
        imageStates[image.getId()] = {'name':image.getName(), 'tokens':imageTokenStates}
        imageDetails.append(imageDetail)
    # Sort imageDetails
    imageDetails.sort(key=lambda name: name['name'].lower())

    # How this works:
    # tokenTags is a list of the tokens involved in all the images. These contain details of the tags that match
    # imageDetails is a list of the images, each one has details per-above tokens. e.g. If the token is matched,
    # has a tag already selected or if it should be auto-selected 

    #print 'tokenTags: ', tokenTags          #PRINT
    #print 'imageDetails: ', imageDetails    #PRINT

    return tokenTags, imageDetails, imageStates


@login_required(setGroupContext=True)
@render_response()
def process_update(request, conn=None, **kwargs):
    if request.method == "POST":
        
        tokenTagsPost = request.POST.getlist('tokentag')
        serverSelectedPost = request.POST.getlist('serverselected')
        checkedPost = request.POST.getlist('imagechecked')

        # Convert the posted data into something more manageable
        # tokenTags = { tokenName: tagId }
        tokenTags = {}
        for tokenTag in tokenTagsPost:
            # Only if there is a selection made
            if len(tokenTag) > 0:
                tokenName,tagId = tokenTag.rsplit(r'_', 1)
                tokenTags[tokenName] = long(tagId)
        print 'tokenTags:', tokenTags     #PRINT

        # serverSelected = { imageId: [tokenName]}
        serverSelected = {}
        for s in serverSelectedPost:
            imageId,tokenName = s.split(r'_',1)
            serverSelected.setdefault(long(imageId), []).append(tokenName)
        # checked = { imageId: [tokenName] }
        #TODO Unmapped tokens checkboxes should probably be disabled on the form until there is a mapping.
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
                
        print 'additions:', additions   #PRINT 
        print 'removals:', removals     #PRINT
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
    tags = []
    for t in conn.getObjects("TagAnnotation"):
        tags.append({'id':t.id,
            'name':t.getTextValue()})
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

    return {'id':tag.id.val, 'name':tag.textValue.val}

@login_required(setGroupContext=True)
@render_response()
def get_tag_on_images(request, conn=None, **kwargs):
    """
    Given a TagId and a list of images, determine the tagged status for each
    """

    imageIdList = [1,2,3]
    tagId = "R3D"

    links = conn.getAnnotationLinks("Image", parent_ids=imageIdList, ann_ids=[tagId], params=params)

    tagOnImages = []
    # The above returns image->tag links that were not specified for deletion, so only delete the appropriate ones 
    for link in links:
        tagOnImages.append(link.parent.id.val)

    print 'tagsOnImages', tagsOnImages

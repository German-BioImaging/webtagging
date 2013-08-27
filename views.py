from django.http import HttpResponse

from omeroweb.webclient.decorators import login_required, render_response

import omero
from omero.model import TagAnnotationI
from omero.rtypes import rstring

from utils import parse_path, createTagAnnotationsLinks

from urlparse import parse_qsl


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

    tokenTags, imageDetails = build_table_data(conn, images)
    # We only need to return a dict - the @render_response() decorator does the rest...
    context = {'template': 'webtagging/tags_from_names.html'}
    context['tokenTags'] = tokenTags
    context['imageDetails'] = imageDetails
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
    for image, allTokens in imagesTokens.iteritems():

        # Create mapping of tags that exist already on this image (tagValue : [ids])
        #TODO Add any manually added mappings to this list
        imageTags = {}
        for tag in listTags(image):
            if tag.getValue() in imageTags:
                imageTags[tag.getValue()].append(tag.getId())
            else:
                imageTags[tag.getValue()] = [tag.getId()]

        #TODO Currently I set one hidden field for tokens that have a single tag match
        # This is adequate, but will require a lot of additional javascript to work
        # What if a token has many matches? There would be no hidden field set, thus no data about which tags may be selected server side
        #       ajax queries will be required to get data about the current selected drop down in order to update the cell-backgrounds and checked status
        #       It will also require javascript to update/add the hidden field so that form submission can carry the selected status forward.
        # Possible alternate solution:
        #   Add a hidden field for each image->tag link. Replaces current image->token link.
        #       This will require javascript to update the cell-backgrounds and checked status when the dropdown value is changed
        #       It will also require javascript to add a new hidden field when adding a new tag mapping as a prelude to updating the cell-backgrounds and checked statuses
        #
        #   

        imageTokens = []
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
                #TODO or are manually added
                if token['name'] in imageTags:
                    # Add the tagIds that match to this token
                    imageToken['tags'] = imageTags[token['name']]

                    # If there is just the one matching tag for this column, mark the token selected
                    if len(token['tags']) == 1:
                        imageToken['selected'] = True


                imageTokens.append(imageToken)


        imageDetail = {'id':image.getId(), 'name':image.getName(), 'tokens':imageTokens}
        imageDetails.append(imageDetail)


    # How this works:
    # tokenTags is a list of the tokens involved in all the images. These contain details of the tags that match
    # imageDetails is a list of the images, each one has details per-above tokens. e.g. If the token is matched,
    # has a tag already selected or if it should be auto-selected 

    print 'tokenTags: ', tokenTags          #PRINT
    print 'imageDetails: ', imageDetails    #PRINT

    return tokenTags, imageDetails


@login_required(setGroupContext=True)
@render_response()
def process_update(request, conn=None, **kwargs):
    if request.method == "POST":
        #controls = parse_qsl(request.raw_post_data, keep_blank_values=True)
        
        tokenTagsPost = request.POST.getlist('tokentag')
        serverSelectedPost = request.POST.getlist('serverselected')
        checkedPost = request.POST.getlist('imagechecked')
        imagesPost = request.POST.getlist('image')

        # Convert the posted data into something more manageable
        #TODO Potential problem with underscore in tag name.
        tokenTags = {}
        for tokenTag in tokenTagsPost:
            # Only if there is a selection made
            if len(tokenTag) > 0:
                n,v = tokenTag.split(r'_')
                tokenTags[n] = long(v)
        print 'tokenTags:', tokenTags     #PRINT

        serverSelected = {}
        for s in serverSelectedPost:
            imageId,tokenName,tagId = s.split(r'_')
            if long(imageId) in serverSelected:
                serverSelected[long(imageId)].append((tokenName,long(tagId)))
            else:
                serverSelected[long(imageId)] = [(tokenName,long(tagId))]

        checked = {}
        for c in checkedPost:
            n,v = c.split(r'_')
            if long(n) in checked:
                checked[long(n)].append(v)
            else:
                checked[long(n)] = [v]

        # Use simple list for images for now, if I need more info I many need a list of dicts or a list of tuples
        # Or if I need to search it, a dictionary instead of the list
        imageIds = [long(image) for image in imagesPost]

        additions = []
        removals = []
        # Create a list of tags to add on images and one to remove tags from images
        for imageId in imageIds:

            # If the image has some checked items
            if imageId in checked or imageId in serverSelected:
                # Not every image will have both of these so have to default to empty list
                # These are the ids of the tag
                checkedTags = []
                selectedTags = []

                # If there are checked checkboxes for this image
                if imageId in checked:
                    # checked[imageId] is the list of token names that have been checked, resolve to tagIds
                    for token in checked[imageId]:
                        # Ensure there is a mapping for this token
                        if token in tokenTags:
                            # Add the id to the list of checked tags
                            checkedTags.append(tokenTags[token])

                # If there are server selected tags for this image
                if imageId in serverSelected:
                    # serverSelected[imageId] is the list of tagIds that are selected along with the token they represent (<tokenName>,<tagId>)
                    # We are only concerned with the current mapping
                    for s in serverSelected[imageId]:
                        if s[0] in tokenTags:
                            selectedTags.append(s[1])
                            break



                # Add any tags (for addition) that are not preexisting (checked - serverSelected)
                additionsTags = list(set(checkedTags) - set(selectedTags))
                # Add any tokens (for removal) that are prexisiting but not checked (serverSelected - checked)
                removalsTags = list(set(selectedTags) - set(checkedTags))
                print 'imageId: ', imageId
                print 'checked:', checkedTags   #PRINT 
                print 'selected:', selectedTags     #PRINT
                print 'additions:', additionsTags   #PRINT 
                print 'removals:', removalsTags     #PRINT
                print

                for tagId in additionsTags:
                    additions.append((imageId, tagId))

                for tagId in removalsTags:
                    removals.append((imageId, tagId))
                
#        print 'additions:', additions   #PRINT 
#        print 'removals:', removals     #PRINT
        return
        createTagAnnotationsLinks(conn, additions, removals)

    # Now we re-build the tagging table and return it
    context = {'template': 'webtagging/tag_table.html'}

    images = list(conn.getObjects("Image", imageIds))
    images.sort(key=lambda img: img.getName().lower())

    tokenTags, imageDetails = build_table_data(conn, images)
    # We only need to return a dict - the @render_response() decorator does the rest...
    context['tokenTags'] = tokenTags
    context['imageDetails'] = imageDetails
    return context


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

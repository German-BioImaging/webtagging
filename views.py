from django.http import HttpResponse

from omeroweb.webclient.decorators import login_required, render_response

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
    tokens = []
    for image in images:
        name = image.getName()

        path_tokens, file_tokens, ext_tokens = parse_path(name)
        tokens.extend(path_tokens)
        tokens.extend(file_tokens)
        #TODO As mentioned below (about 40 lines) extension tags are ignored for now
        #tokens.extend(ext_tokens)

    # remove duplicates
    tokens = list(set(tokens))
    tokens.sort(key=lambda name: name.lower())


    # find which tokens match existing Tags
    tokenTags = []
    for token in tokens:

        # Skip zero length tokens
        if len(token) == 0:
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
        tokenTags.append(tokenTagMap)

    # Populate the images with details
    imageDetails = []
    for image in images:
        pathTokens, fileTokens, extTokens = parse_path(image.getName())
        #TODO allTokens needs to be controlled by some form elements, e.g. extension/directory support on/off
        # Potentially each list of tokens would be treated differently so searched separately 
        # Ignore extTokens for now
        allTokens = pathTokens + fileTokens

        # Create mapping of tags that exist already on this image (value : id)
        #TODO Inadequate if there are multiple tags with the same value
        imageTags = {}
        for tag in listTags(image):
            imageTags[tag.getValue()] = tag.getId()

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
        for token in tokenTags:
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
                        # Mark the token for autoselect
                        imageToken['autoselect'] = True
            # If the tag is already on the image (not necessarily because it has a matching token)
            if token['name'] in imageTags:
                # Mark the token as selected
                #TODO Inadequate if there are multiple tags with the same value as this merely marks the token as matching 
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
        
        #In django > 1.4
        #controls = request.POST.dict()
        controls = request.POST.iterlists()
        tokenTagsPost = request.POST.getlist('tokentag')
        historyPost = request.POST.getlist('imagechecked_history')
        checkedPost = request.POST.getlist('imagechecked')
        imagesPost = request.POST.getlist('image')

        # Convert the posted data into something more manageable
        tokenTags = {}
        for tokenTag in tokenTagsPost:
            n,v = tokenTag.split(r'_')
            tokenTags[n] = long(v)
        print 'tokenTags:', tokenTags     #PRINT

        history = {}
        for h in historyPost:
            n,v = h.split(r'_')
            if long(n) in history:
                history[long(n)].append(v)
            else:
                history[long(n)] = [v]

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
            if imageId in checked or imageId in history:
                # Not every image will have both of these so have to default to empty list
                checkedTokens = []
                selectedTokens = []
                if imageId in checked:
                    checkedTokens = checked[imageId]
                if imageId in history:
                    selectedTokens = history[imageId]

                # Add any tokens (for addition) that are not preexisting (checked - selected)
                additionsTokens = list(set(checkedTokens) - set(selectedTokens))
                # Add any tokens (for removal) that are prexisiting but not checked (selected - checked)
                removalsTokens = list(set(selectedTokens) - set(checkedTokens))

                # Lookup which tag is mapped to the tokens that are to be added/removed
                for token in additionsTokens:
                    # Currently the submitted tokens include ones with no mapping, simply ignore these
                    if token in tokenTags:
                        additions.append((imageId, tokenTags[token]))

                for token in removalsTokens:
                    # Currently the submitted tokens include ones with no mapping, simply ignore these
                    if token in tokenTags:
                        removals.append((imageId, tokenTags[token]))
                
        print 'additions:', additions   #PRINT 
        print 'removals:', removals     #PRINT
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
   

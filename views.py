from django.http import HttpResponse

from omeroweb.webclient.decorators import login_required, render_response

from utils import parse_path

def index(request):
    """
    Just a place-holder, base for creating urls etc
    """

    return HttpResponse("Welcome to webtagging")


@login_required()
@render_response()
def auto_tag(request, datasetId=None, conn=None, **kwargs):
    """
    List all the images in a table, with their names tokenised to create 
    suggestions for new tags.
    Indicate where these match existing tags etc.
    """

    def listTags(image):
        """ This should be in the BlitzGateway! """
        return [a for a in image.listAnnotations() if a.__class__.__name__ == "TagAnnotationWrapper"]

    # TODO: handle list of Image IDs. Currently we ONLY support Dataset
    if datasetId is not None:
        dataset = conn.getObject("Dataset", datasetId)
        images = list( dataset.listChildren() )
        images.sort(key=lambda img: img.getName().lower())

    # Need to build our table...

    # First go through all images, getting all the tokens
    tokens = []
    for image in images:
        name = image.getName()

        path_tokens, file_tokens, ext_tokens = parse_path(name)
        tokens.extend(path_tokens)
        tokens.extend(file_tokens)
        tokens.extend(ext_tokens)

    # remove duplicates
    tokens = list(set(tokens))
    tokens.sort(key=lambda name: name.lower())


    # find which tokens match existing Tags
    # Each column is a Tag or a Token.
    tagCols = []    # {"name": Tag, "id":<id>} or {"name":Tag} for new tags
    for tk in tokens:
        if len(tk) == 0:
            continue
        tags = list(conn.getObjects("TagAnnotation", attributes={'textValue':tk}))
        if len(tags) == 1:
            # Column is a Tag
            tagCols.append({'name':tk, 'id':tags[0].getId()})
        elif len(tags) > 1:
            pass    # TODO: Assume Tags are unique for each token? #DPWR: Will have to offer a dropdown box as it's very likely a choice will have to be made
        else:
            tagCols.append({'name':tk})     # No Tag - just a token


    # Now we can populate the table data - One row (image) at at time...
    tagRows = []
    for image in images:
        name = image.getName()

        path_tokens, file_tokens, ext_tokens = parse_path(name)
        tt = path_tokens + file_tokens + ext_tokens

        # Create mapping of tags for this image (value : id)
        imgTags = {}
        for tag in listTags(image):
            imgTags[tag.getValue()] = tag.getId()


        tableCells = []
        # for each column/token of the row, get all the info we need for each cell...
        for tagCol in tagCols:
            colName = tagCol["name"]
            # if the image has the column in it's tokens...
            if colName in tt:
                td = {}

                # If the column/token is an Existing Tag, provide the ID
                if 'id' in tagCol:
                    td['tagId'] = tagCol['id']	# Also indicates 'Matched'

                    # Determine if the Tag is already on the image
                    if colName in imgTags:
                        td['selected'] = True
                    #else:
                        #td['selected'] = False 	# Implicit

                tableCells.append(td)
            else:
                tableCells.append({"text":""})
        # Row Data has imageId, name, and tag/token data
        tagRows.append({'id':image.id, 'name':name, 'tableCells':tableCells})

    # We only need to return a dict - the @render_response() decorator does the rest...
    context = {'template': 'webtagging/tags_from_names.html'}
    context['tagCols'] = tagCols
    context['tagRows'] = tagRows
    return context









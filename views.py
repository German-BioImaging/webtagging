from django.http import HttpResponse

from omeroweb.webclient.decorators import login_required, render_response


def index(request):
    """
    Just a place-holder, base for creating urls etc
    """

    return HttpResponse("Welcome to webtagging")


@login_required()
@render_response()
def tags_from_names(request, datasetId=None, conn=None, **kwargs):
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

    # First go through all images, getting all the name tokens
    tokens = []
    for image in images:
        name = image.getName()
        tt = name.split(r'/')       # TODO: improve regex
        tokens.extend(tt)

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
            pass    # TODO: Assume Tags are unique for each token?
        else:
            tagCols.append({'name':tk})     # No Tag - just a token


    # Now we can populate the table data - One row (image) at at time...
    tagRows = []
    for image in images:
        name = image.getName()
        tt = name.split(r'/')
        imgTags = {}
        for tag in listTags(image):
            imgTags[tag.getValue()] = tag.getId()

        tableCells = []
        # for each column of the row, get all the info we need for each cell...
        for tagCol in tagCols:
            colName = tagCol["name"]
            # if the image has the column in it's tokens...
            if colName in tt:
                td = {"text":"TAGGED"}
                # And if it's not already a Tag on the image, show an "Add" button
                if colName not in imgTags:
                    td['text'] = "ADD"
                    td['ADD'] = True
                    # If the column/token is an Existing Tag, provide the ID
                    if 'id' in tagCol:
                        td['tagId'] = tagCol['id']
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









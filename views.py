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
        return [a for a in image.listAnnotations() if a.__class__.__name__ == "TagAnnotation"]

    if datasetId is not None:
        dataset = conn.getObject("Dataset", datasetId)
        images = list( dataset.listChildren() )
        images.sort(key=lambda img: img.getName().lower())

    # Need to build our table
    tagCols = {}     # All tags. {"Name": <id>} or {"Name":None} for new tags
    tagRows = []

    for image in images:

        name = image.getName()
        tokens = name.split(r'/')       # TODO: improve regex
        tags = {}
        for tag in listTags(image):
            tags[tag.getValue()] = tag.getId()

        imgTags = {}
        for t in tokens:
            if t in tags:
                imgTags[t] = tags[t]
                tagCols[t] = tags[t]    # {'text':id}
            else:
                imgTags[t] = None
                if t not in tagCols:    # Don't overwrite
                    tagCols[t] = None

        tagRows.append({'id':image.id, 'name':image.name, 'tags':imgTags})

    # Now we know all the column names, we can organise tags for each row into cols...

    # convert to list
    # tagCols = [{value:tid} for value,tid in tagCols.items()]
    # tagCols.sort(key=lambda tag:tag.keys()[0])
    tagCols = tagCols.keys()
    tagCols.sort(key=lambda tag: tag.lower())

    print tagCols

    for row in tagRows:
        tagDict = row['tags']
        tagCells = []       # <td> under tagCols
        print tagDict
        for col in tagCols:
            #tagText = col.keys()[0]
            tagText = col
            if tagText in tagDict:
                tagCells.append(tagText)
            else:
                tagCells.append("")
        print tagCells
        row['tags'] = tagCells

    context = {'template': 'webtagging/tags_from_names.html'}
    context['tagCols'] = tagCols
    context['tagRows'] = tagRows
    return context









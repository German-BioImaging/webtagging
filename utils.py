import omero
#from omero.model import ImageAnnotationLink, ImageI, TagAnnotationI
#from omero.sys import ParametersI, Filter
from omero.rtypes import rlong

def parse_path(path):
    """ 
    TODO: Should take arguments relating to regex
    Splits the path up according to regex and returns lists of tokens
    per seperator.
    Hardcoded for now, one for the path, one for the name, one for the extension
    """

    # Split by '/' to get the path
    path_tokens = path.split(r'/')
    file = path_tokens.pop()

    #TODO Cope with multiple-extensions somehow
    ext_tokens = file.rsplit(r'.')
    file = ext_tokens.pop(0)

    #TODO Cope with multiple separators
    file_tokens = file.split(r'_')

    return path_tokens, file_tokens, ext_tokens

def createTagAnnotationsLinks(conn, additions=[], removals=[]):
    """
    Links or unlinks existing Images with existing Tag annotations 
    
    @param additions:       List of tags to add to images
    @param additions:       List of tags to remove from images
    """

    newLinks = []        
    # Create a list of links to apply
    for addition in additions:
        link = omero.model.ImageAnnotationLink()
        link.parent = omero.model.ImageI(addition[0], False)
        link.child = omero.model.TagAnnotationI(addition[1], False)
        newLinks.append(link)
        print 'adding:', addition[0], '->', addition[1]

    ''' 
    # Apply the links
    failed = 0
    savedLinks = []
    try:
        # will fail if any of the links already exist
        savedLinks = conn.getUpdateService().saveAndReturnArray(newlinks, conn.SERVICE_OPTS)
    except omero.ValidationException, x:
        for l in newLinks:
            try:
                savedLinks.append(self.conn.getUpdateService().saveAndReturnObject(l, conn.SERVICE_OPTS))
            except:
                failed+=1
    '''

    # Get existing links belonging to current user (all at once to save on queries)
    allImageIds, allTagIds = zip(*removals)
    params = omero.sys.Parameters()
    params.theFilter = omero.sys.Filter()
    params.theFilter.ownerId = rlong(conn.getUserId())
    links = conn.getAnnotationLinks("Image", parent_ids=allImageIds, ann_ids=allTagIds, params=params)

    # The above returns image->tag links that were not specified for deletion, so only delete the appropriate ones 
    for link in links:
        if (link.parent.id.val, link.child.id.val) in removals:
            print 'removing: ', link.parent.id.val, '->', link.child.id.val
    

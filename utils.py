import omero
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
        link = omero.model.ImageAnnotationLinkI()
        link.parent = omero.model.ImageI(addition[0], False)
        link.child = omero.model.TagAnnotationI(addition[1], False)
        newLinks.append(link)

    # Apply the links
    failed = 0
    savedLinks = []
    try:
        # will fail if any of the links already exist
        savedLinks = conn.getUpdateService().saveAndReturnArray(newLinks, conn.SERVICE_OPTS)
    except omero.ValidationException, x:
        for l in newLinks:
            try:
                savedLinks.append(self.conn.getUpdateService().saveAndReturnObject(l, conn.SERVICE_OPTS))
            except:
                failed+=1

    if len(removals) > 0:
        # Get existing links belonging to current user (all at once to save on queries)
        allImageIds, allTagIds, allTokenNames = zip(*removals)
        # removalsCheck has to exist because the check to see if the image/tagId combo was in the list, there is no knowledge of the tokenName
        removalsCheck = zip(allImageIds, allTagIds)
        params = omero.sys.Parameters()
        params.theFilter = omero.sys.Filter()
        params.theFilter.ownerId = rlong(conn.getUserId())
        links = conn.getAnnotationLinks("Image", parent_ids=list(allImageIds), ann_ids=list(allTagIds), params=params)
        # The above returns image->tag links that were not specified for deletion, so only delete the appropriate ones 
        for link in links:
            if (link.parent.id.val, link.child.id.val) in removalsCheck:
                conn.deleteObjectDirect(link._obj)

class BlitzSet(object):
    def __init__(self, s=[]):

        self.__items = dict(
            (self.__item_key(i), i) for
             i in s
        )

    def __item_key(self, item):
        return item.getId()

    def add(self, item):
        # To be consistent with python set, do not overwrite existing items
        if not self.__contains__(item):
            self.__items[self.__item_key(item)] = item

    def remove(self, item):
        del self.__items[self.__item_key(item)]

    def update(self, items):
        for item in items:
            # Unlike add, update overwrites existing items
            self.__items[self.__item_key(item)] = item

    def union(self, s):
        # To be consistent with python set, self overrides s
        uni = BlitzSet()
        uni.__items = dict(s.__items, **self.__items)
        return uni

    def __or__(self, s):
        return self.union(s)

    def intersection(self, s):
        # To be consistent with python set, shorter list overrides
        # or s if equal length

        # Determine shorter list for iteration
        if len(self.__items) < len(s.__items):
            s1 = self.__items
            s2 = s.__items
        else:
            s1 = s.__items
            s2 = self.__items

        # Compute the intersection
        inter = BlitzSet()
        for k in s1.iterkeys():
            if k in s2:
                inter.add(s1[k])
        return inter

    def __and__(self, s):
        return self.intersection(s)

    def difference(self, s):
        inter = BlitzSet()
        for k in self.__items.iterkeys():
            if k not in s.__items:
                inter.add(self.__items[k])
        return inter

    def __sub__(self, s):
        return self.difference(s)

    def symmetric_difference(self, s):
        # TODO Performance wise, probably not optimal
        diff1 = self.difference(s)
        diff2 = s.difference(self)
        return diff1.union(diff2)

    def __xor__(self, s):
        return self.symmetric_difference(s)

    def __str__(self):
        return str(self.__items.values())

    def __contains__(self, item):
        return self.__item_key(item) in self.__items

    def __iter__(self):
        return self.__items.itervalues()

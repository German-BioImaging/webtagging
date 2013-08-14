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
    file = ext_tokens[0]

    #TODO Cope with multiple separators
    file_tokens = file.split(r'_')

    return path_tokens, file_tokens, ext_tokens

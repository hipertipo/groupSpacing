import json
from mojo.tools import IntersectGlyphWithLine

PREFIX_LEFTSIDE  = 'public.kern2.'
PREFIX_RIGHTSIDE = 'public.kern1.'

def getMargins(glyph, beam=None):
    '''
    Get left and right margins for a glyph.

    Args:
        glyph (RGlyph): A glyph object.
        beam (int or None): A beam to measure the margins. (optional)

    Returns:
        A tuple with left and right margins, or None if the beam does not intersect any contours.

    >>> glyph = CurrentGlyph()
    >>> sp = CurrentSpaceCenter()
    >>> beam = sp.beam()
    >>> print(glyph.name, beam, getMargins(glyph, beam))

    '''
    if beam is None:
        return glyph.leftMargin, glyph.rightMargin

    else:
        line = (-1000, beam), (glyph.width + 1000, beam)
        intersections = IntersectGlyphWithLine(glyph, line, canHaveComponent=True, addSideBearings=True)
        intersections.sort()

        if not len(intersections) > 2:
            return

        leftMargin = intersections[1][0] - intersections[0][0]
        rightMargin = intersections[-1][0] - intersections[-2][0]

        return leftMargin, rightMargin

def getGroupsForGlyph(glyph):
    '''
    Get left and right spacing groups for a glyph.

    Returns:
        A tuple with left and right spacing groups. Each spacing group can be the name of the group (str) or None.

    >>> glyph = CurrentGlyph()
    >>> print(getGroupsForGlyph(glyph))
    ('com.hipertipo.groupSpacing.leftSide.n', 'com.hipertipo.groupSpacing.rightSide.n')

    '''
    font = glyph.font

    groupsLeftSide = []
    groupsRightSide = []

    for groupName in font.groups.keys():
        group = font.groups[groupName]

        if groupName.startswith(PREFIX_LEFTSIDE):
            if glyph.name in group:
                groupsLeftSide.append(groupName)

        if groupName.startswith(PREFIX_RIGHTSIDE):
            if glyph.name in group:
                groupsRightSide.append(groupName)

    if len(groupsLeftSide) > 1 or len(groupsLeftSide) > 1:
        print('glyph is in more than one group: %s' % ' '.join(groupsLeftSide))

    groupLeftSide = groupsLeftSide[0] if groupsLeftSide else None
    groupRightSide = groupsRightSide[0] if groupsRightSide else None

    return groupLeftSide, groupRightSide

def copyMargins(glyph, siblings, side, beam=None, allLayers=False, verbose=True):
    '''
    Copy left or right margin from one glyph to all other glyphs in the same spacing group.

    Args:
        glyph (RGlyph): The glyph from which the margin will be copied.
        siblings (list): A list of names of other glyphs in the same spacing group.
        side (str): The side of the spacing group: `left` or `right`.
        beam (int or None): A beam to measure the margins. (optional)
        verbose (bool): Print information when copying margins.

    >>> side = 'right'
    >>> glyph = CurrentGlyph()
    >>> siblings = getSiblings(glyph, side)
    >>> spaceCenter = CurrentSpaceCenter()
    >>> copyMargins(glyph, siblings, side, beam=spaceCenter.beam())

    '''
    left, right = getMargins(glyph, beam)

    font = glyph.font
    if not font:
        return

    siblings.remove(glyph.name)

    layerNames = font.layerOrder if allLayers else [glyph.layer.name]

    if verbose:
        print(f"transferring {side} margins…\n")
        print(f"\tvalue   : {right if side == 'right' else left} {'(beam)' if beam else ''}")
        print(f"\tlayers  : {' '.join(layerNames)}")
        print(f"\tsource  : {glyph.name}")
        print(f"\ttargets : {' '.join(siblings)}")
        print()

    for layerName in layerNames:

        # if verbose:
        #     print(f'\t{layerName}')

        for glyphName in siblings:
            sibling = font[glyphName].getLayer(layerName)

            if sibling.bounds is None:
                continue

            sibling.prepareUndo()

            # if verbose:
            #     print(f'\t\tcopying {side} margin from {glyph.name} to {sibling.name}...')

            if beam is None:
                if side == 'right':
                    difference = glyph.rightMargin - sibling.rightMargin
                    sibling.rightMargin = glyph.rightMargin
                else:
                    difference = glyph.leftMargin - sibling.leftMargin
                    sibling.leftMargin = glyph.leftMargin

            else:
                leftSibling, rightSibling = getMargins(sibling, beam)
                if side == 'right':
                    difference = right - rightSibling
                    sibling.rightMargin += difference
                else:
                    difference = left - leftSibling
                    sibling.leftMargin += difference

            sibling.performUndo()
            sibling.changed()

        # if verbose:
        #     print()

    if verbose:
        print('...done.\n')

def getSiblings(glyph, side):
    '''
    Get all glyphs in the same left or right spacing group of a given glyph.

    >>> glyph = CurrentGlyph()
    >>> side = ['left', 'right'][0]
    >>> print(glyph.name, side, getSiblings(glyph, side))

    '''
    groupLeftSide, groupRightSide = getGroupsForGlyph(glyph)

    if side == 'right':
        siblings = list(glyph.font.groups[groupRightSide]) if groupRightSide is not None else []
    else:
        siblings = list(glyph.font.groups[groupLeftSide]) if groupLeftSide is not None else []

    # if glyph.name in siblings:
    #     siblings.remove(glyph.name)
    
    return siblings

def getSpacingGroups(font):
    '''
    Get all spacing groups in the font as a dictionary.

    >>> font = CurrentFont()
    >>> spacingGroups = getSpacingGroups()
    >>> print(spacingGroups.keys())

    '''
    return { groupName : font.groups[groupName] for groupName in font.groups.keys() if groupName.startswith(PREFIX_LEFTSIDE) or groupName.startswith(PREFIX_RIGHTSIDE) }

def exportSpacingGroups(font, filePath):
    '''
    Export spacing groups to .json file.

    >>> font = CurrentFont()
    >>> filePath = PutFile(message='export spacing groups', fileName='spacingGroups.json')
    >>> exportSpacingGroups(font, filePath)

    '''
    msg = 'export spacing groups to .json file'
    spacingGroups = getSpacingGroups(font)
    with open(filePath, 'w', encoding='utf-8') as f:
        json.dump(spacingGroups, f, indent=2)

def importSpacingGroups(font, filePath):
    '''
    Import spacing groups from .json file.

    >>> font = CurrentFont()
    >>> filePath = GetFile(message='import spacing groups', fileTypes=['json'])
    >>> importSpacingGroups(font, filePath)

    '''
    msg = 'import spacing groups from .json file'
    with open(filePath, 'r', encoding='utf-8') as f:
        groups = json.load(f)
    for group in groups:
        font.groups[group] = groups[group]

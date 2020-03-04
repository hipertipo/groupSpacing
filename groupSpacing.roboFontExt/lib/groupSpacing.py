from vanilla import FloatingWindow, RadioGroup, SquareButton, CheckBox
from mojo.events import addObserver, removeObserver
from mojo.drawingTools import *
from mojo.UI import CurrentSpaceCenter, PutFile, GetFile
from mojo.roboFont import OpenWindow
from mojo.tools import IntersectGlyphWithLine
from defconAppKit.windows.baseWindow import BaseWindowController
import json

# ----------------
# global variables
# ----------------

PREFIX_LEFTSIDE  = 'public.kern2.' # 'groupSpacing.left.'
PREFIX_RIGHTSIDE = 'public.kern1.' # 'groupSpacing.right.'

# ---------
# functions
# ---------

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

    if verbose:
        print(f'source glyph: {glyph.name} ({side})')

    for glyphName in siblings:

        sibling = font[glyphName]

        if sibling.bounds is None:
            continue

        if glyph == sibling:
            continue

        sibling.prepareUndo()
        print(f'copying {side} margin to {sibling}...')

        if beam is None:

            if side == 'right':
                difference = glyph.rightMargin - sibling.rightMargin
                sibling.rightMargin = glyph.rightMargin
            else: # left side
                difference = glyph.leftMargin - sibling.leftMargin
                sibling.leftMargin = glyph.leftMargin

            if allLayers:
                for layerName in font.layerOrder:
                    print(layerName)
                    if layerName == glyph.layer.name:
                        continue
                    layerGlyph = glyph.getLayer(layerName)
                    print(layerGlyph)
                    if side == 'right':
                        layerGlyph.rightMargin += difference
                    else: # left side
                        layerGlyph.leftMargin += difference

        else:
            leftSibling, rightSibling = getMargins(sibling, beam)
            if side == 'right':
                difference = right - rightSibling
                sibling.rightMargin += difference
            else: # left side
                difference = left - leftSibling
                sibling.leftMargin += difference

        sibling.performUndo()
        sibling.changed()

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

# -------
# objects
# -------

class GroupSpacingWindow(BaseWindowController):

    '''
    A tool to enable group spacing in the Space Center.

    - works with the selected glyph in the Space Center
    - shows a preview of all other glyphs in the same spacing group
    - transfer margins from current glyph to all glyphs in the same spacing group
    - supports measurements using the current beam

    '''

    def __init__(self):
        padding = 10
        lineHeight = 20
        buttonHeight = 25
        width = 123
        height = lineHeight * 3 + buttonHeight * 4 + padding * 7

        self.w = FloatingWindow((width, height), title='spacing')

        x = y = padding
        self.w.makeGroupButton = SquareButton(
                (x, y, -padding, buttonHeight),
                'make group',
                callback=self.makeGroupCallback,
                sizeStyle='small')

        y += buttonHeight + padding
        self.w.side = RadioGroup(
                (x, y, -padding, lineHeight),
                ['left', 'right'],
                isVertical=False,
                callback=self.updateViewsCallback,
                sizeStyle='small')
        self.w.side.set(0)

        y += lineHeight + padding
        self.w.copySpacingButton = SquareButton(
                (x, y, -padding, buttonHeight),
                'copy margin',
                callback=self.copySpacingCallback,
                sizeStyle='small')

        y += buttonHeight + padding
        self.w.useBeam = CheckBox(
                (x, y, -padding, lineHeight),
                'use beam',
                callback=self.updateViewsCallback,
                sizeStyle='small')

        y += lineHeight
        self.w.allLayers = CheckBox(
                (x, y, -padding, lineHeight),
                'all layers',
                callback=self.updateViewsCallback,
                sizeStyle='small')

        y += lineHeight + padding
        self.w.exportButton = SquareButton(
                (x, y, -padding, buttonHeight),
                'export…',
                callback=self.exportCallback,
                sizeStyle='small')

        y += buttonHeight + padding
        self.w.importButton = SquareButton(
                (x, y, -padding, buttonHeight),
                'import…',
                callback=self.importCallback,
                sizeStyle='small')

        self.setUpBaseWindowBehavior()

        addObserver(self, "drawGlyphsInGroup", "spaceCenterDraw")

        self.w.open()

    # dynamic attrs.

    @property
    def side(self):
        '''The selected spacing group side.'''
        return ['left', 'right'][int(self.w.side.get())]

    @property
    def useBeam(self):
        '''Use or not the beam to measure margins. Value taken from the checkbox.'''
        return self.w.useBeam.get()

    @property
    def allLayers(self):
        '''Set margins in all layers. Value taken from the checkbox.'''
        return self.w.allLayers.get()

    @property
    def beam(self):
        '''The beam’s y position in the Space Center.'''
        sp = CurrentSpaceCenter()
        if not sp:
            return
        return sp.beam()

    # ---------
    # callbacks
    # ---------

    def makeGroupCallback(self, sender):
        '''Make a new spacing group with the selected glyph.'''

        glyph = CurrentGlyph()
        if not glyph:
            return

        if glyph.font is None:
            return

        prefix = PREFIX_LEFTSIDE if self.side == 'left' else PREFIX_RIGHTSIDE
        groupName = prefix + glyph.name
        if not groupName in glyph.font.groups:
            glyph.font.groups[groupName] = [glyph.name]

    def copySpacingCallback(self, sender):
        '''Copy margin from current glyph to other glyphs in left/right spacing class.'''

        glyph = CurrentGlyph()

        if not glyph:
            return

        if glyph.bounds is None:
            return

        if glyph.font is None:
            return

        siblings = getSiblings(glyph, self.side)

        if not siblings:
            return

        beam = self.beam if self.useBeam else None
        copyMargins(glyph, siblings, self.side, beam=beam, allLayers=self.allLayers)

    def exportCallback(self, sender):
        '''Export spacing groups to .json file.'''
        font = CurrentFont()
        filePath = PutFile(message='export spacing groups', fileName='spacingGroups.json')
        exportSpacingGroups(font, filePath)

    def importCallback(self, sender):
        '''Import spacing groups from .json file.'''
        font = CurrentFont()
        filePath = GetFile(message='import spacing groups', fileTypes=['json'])
        importSpacingGroups(font, filePath)

    def windowCloseCallback(self, sender):
        '''Remove observers when closing window.'''
        super().windowCloseCallback(sender)
        removeObserver(self, "spaceCenterDraw")

    def updateViewsCallback(self, sender):
        '''Update the Space Center.'''
        g = CurrentGlyph()
        if g is not None:
            g.changed()

    # ---------
    # observers
    # ---------

    def drawGlyphsInGroup(self, notification):
        '''Display all glyphs belonging to the same spacing group in the background.'''

        glyph = notification['glyph']

        font = glyph.font
        if font is None:
            return

        siblings = getSiblings(glyph, self.side)
        if not siblings:
            return

        if not notification['selected']:
            return

        # get colors based on display mode
        S = CurrentSpaceCenter()
        if not S:
            return
        inverse = S.glyphLineView.getDisplayStates()['Inverse']
        foreground = (1,) if inverse else (0,)
        background = (0,) if inverse else (1,)

        fill(*background)
        stroke(*background)
        drawGlyph(glyph)
        stroke(None)

        alpha = 1.0 / len(siblings)

        for glyphName in siblings:

            save()

            if self.side == 'right':
                dx = glyph.width - font[glyphName].width
                translate(dx, 0)

            color = foreground + (0.6,) if glyphName == glyph.name else foreground + (alpha,)
            fill(*color)
            drawGlyph(font[glyphName])

            restore()

# -------
# testing
# -------

if __name__ == '__main__':

    OpenWindow(GroupSpacingWindow)

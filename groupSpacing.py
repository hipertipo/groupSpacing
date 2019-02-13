from vanilla import FloatingWindow, RadioGroup, Button, CheckBox
from mojo.events import addObserver, removeObserver
from mojo.drawingTools import *
from mojo.UI import CurrentSpaceCenter
from mojo.roboFont import OpenWindow
from mojo.tools import IntersectGlyphWithLine
from defconAppKit.windows.baseWindow import BaseWindowController

PREFIX_LEFTSIDE = 'com.hipertipo.groupSpacing.leftSide.' # 'public.kern2.'
PREFIX_RIGHTSIDE = 'com.hipertipo.groupSpacing.rightSide.' # 'public.kern1.'

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

def copyMargins(glyph, siblings, side, beam=None, verbose=True):
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

    if verbose:
        print('%s (%s) → %s' % (glyph.name, 'L' if side == 'left' else 'R', ' '.join(siblings)))

    for glyphName in siblings:

        sibling = glyph.font[glyphName]
        if sibling.bounds is None:
            continue

        sibling.prepareUndo()

        if beam is None:
            if side == 'right':
                sibling.rightMargin = glyph.rightMargin
            else: # left
                sibling.leftMargin = glyph.leftMargin

        else:
            leftSibling, rightSibling = getMargins(sibling, beam)
            if side == 'right':
                difference = right - rightSibling
                sibling.rightMargin += difference
            else: # left
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
        return glyph.font.groups[groupRightSide] if groupRightSide is not None else []
    else:
        return glyph.font.groups[groupLeftSide] if groupLeftSide is not None else []

class GroupSpacingWindow(BaseWindowController):

    def __init__(self):
        padding = 10
        lineHeight = 22
        width = 123
        height = lineHeight * 3 + padding * 4

        self.w = FloatingWindow(
                (width, height),
                title='spacing')

        x = y = padding
        self.w.side = RadioGroup(
                (x, y, -padding, lineHeight),
                ['left', 'right'],
                isVertical=False,
                callback=self.updateViewsCallback,
                sizeStyle='small')
        self.w.side.set(0)

        y += lineHeight + padding
        self.w.copySpacingButton = Button(
                (x, y, -padding, lineHeight),
                'copy',
                callback=self.buttonCallback,
                sizeStyle='small')

        y += lineHeight + padding
        self.w.useBeam = CheckBox(
                (x, y, -padding, lineHeight),
                'use beam',
                callback=self.updateViewsCallback,
                sizeStyle='small')

        self.setUpBaseWindowBehavior()

        addObserver(self, "drawGlyphsInGroup", "spaceCenterDraw")

        self.w.open()

    # dynamic attrs.

    @property
    def side(self):
        '''The selected space group side.'''
        return ['left', 'right'][int(self.w.side.get())]

    @property
    def useBeam(self):
        '''Use or not the beam to measure margins. Value taken from the checkbox.'''
        return self.w.useBeam.get()

    @property
    def beam(self):
        '''The beam’s y position in the Space Center.'''
        sp = CurrentSpaceCenter()
        if not sp:
            return
        return sp.beam()

    # callbacks

    def buttonCallback(self, sender):
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

        copyMargins(glyph, siblings, self.side, beam=self.beam)

    def windowCloseCallback(self, sender):
        '''Remove observers when closing window.'''
        super().windowCloseCallback(sender)
        removeObserver(self, "spaceCenterDraw")

    def updateViewsCallback(self, sender):
        '''Update the Space Center.'''
        g = CurrentGlyph()
        if g is not None:
            g.changed()

    # observers

    def drawGlyphsInGroup(self, notification):

        glyph = notification['glyph']

        font = glyph.font
        if font is None:
            return

        siblings = getSiblings(glyph, self.side)
        if not siblings:
            return

        if not notification['selected']:
            # mark other glyphs in group?
            if glyph.name in siblings:
                pass
            return

        alpha = 1.0 / len(siblings)
        fill(0, alpha)

        for glyphName in siblings:
            if glyphName == glyph.name:
                continue

            sibling = font[glyphName]

            save()
            if self.side == 'right':
                dx = glyph.width - sibling.width
                translate(dx, 0)
            drawGlyph(sibling)
            restore()

if __name__ == '__main__':

    GroupSpacingWindow()

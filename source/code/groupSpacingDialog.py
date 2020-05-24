from importlib import reload
import groupSpacingLib
reload(groupSpacingLib)

from vanilla import HUDFloatingWindow, RadioGroup, Button, CheckBox, Slider, TextBox
from mojo.events import addObserver, removeObserver
from mojo.drawingTools import *
from mojo.roboFont import CurrentGlyph, CurrentFont
from mojo.UI import CurrentSpaceCenter, PutFile, GetFile, getDefault
from defconAppKit.windows.baseWindow import BaseWindowController

from groupSpacingLib import *

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
        buttonHeight = 20
        width = 123
        height  = lineHeight * 6 + buttonHeight * 4 + padding * 9

        self.w = HUDFloatingWindow((width, height), title='group spacing')

        x = y = padding
        self.w.makeGroupButton = Button(
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
        self.w.copySpacingButton = Button(
                (x, y, -padding, buttonHeight),
                'copy margin',
                callback=self.copySpacingCallback,
                sizeStyle='small')

        y += buttonHeight + padding
        self.w.useBeam = CheckBox(
                (x, y, -padding, lineHeight),
                'use beam',
                callback=self.useBeamCallback,
                sizeStyle='small')

        y += lineHeight
        self.w.allLayers = CheckBox(
                (x, y, -padding, lineHeight),
                'all layers',
                callback=self.updateViewsCallback,
                sizeStyle='small')

        y += lineHeight + padding
        self.w.opacityLabel = TextBox(
                (x, y, -padding, lineHeight),
                'opacity:',
                sizeStyle='small')

        y += lineHeight
        self.w.opacity = Slider(
                (x, y, -padding, lineHeight),
                value=0.4, minValue=0.0, maxValue=0.9,
                callback=self.updateViewsCallback,
                sizeStyle='small')

        y += lineHeight + padding
        self.w.exportButton = Button(
                (x, y, -padding, buttonHeight),
                'export…',
                callback=self.exportCallback,
                sizeStyle='small')

        y += buttonHeight + padding
        self.w.importButton = Button(
                (x, y, -padding, buttonHeight),
                'import…',
                callback=self.importCallback,
                sizeStyle='small')

        y += buttonHeight + padding
        self.w.verbose = CheckBox(
                (x, y, -padding, lineHeight),
                'verbose',
                value=True,
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

    @property
    def opacity(self):
        '''The opacity of the fill color of glyphs in group.'''
        return self.w.opacity.get()

    @property
    def verbose(self):
        '''Output action info to the console.'''
        return self.w.verbose.get()

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
        copyMargins(glyph, siblings, self.side, beam=beam, allLayers=self.allLayers, verbose=self.verbose)

    def useBeamCallback(self, sender):
        '''Show/hide the beam according to checkbox selection.'''
        S = CurrentSpaceCenter()
        if not S:
            return
        value = sender.get()
        options = S.glyphLineView.getDisplayStates()
        options['Beam'] = value
        S.glyphLineView.setDisplayStates(options)

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
        S = CurrentSpaceCenter()
        if not S:
            return
        S.glyphLineView.refresh()

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

        S = CurrentSpaceCenter()
        if not S:
            return

        inverse = S.glyphLineView.getDisplayStates()['Inverse']

        # hide solid color glyph
        R, G, B, A = getDefault("spaceCenterBackgroundColor") if not inverse else getDefault("spaceCenterGlyphColor")
        bounds = glyph.bounds
        if bounds:
            save()
            fill(R, G, B, A)
            stroke(R, G, B, A)
            drawGlyph(glyph)
            restore()

        # draw side indicator
        save()
        stroke(1, 0, 0)
        strokeWidth(10)
        xPos = 0 if self.side == 'left' else glyph.width
        yMin = font.info.descender
        yMax = yMin + font.info.unitsPerEm
        line((xPos, yMin), (xPos, yMax))
        restore()

        # draw glyph and siblings
        R, G, B, A = getDefault("spaceCenterGlyphColor") if not inverse else getDefault("spaceCenterBackgroundColor")
        alpha = (1.0 / len(siblings) + self.opacity) / 2
        stroke(None)
        for glyphName in siblings:
            if glyphName not in glyph.layer:
                continue
            g = font[glyphName].getLayer(glyph.layer.name)
            save()
            if self.side == 'right':
                dx = glyph.width - g.width
                translate(dx, 0)
            color = (R, G, B, 0.4) if glyphName == glyph.name else (R, G, B, alpha)
            fill(*color)
            drawGlyph(g)
            restore()


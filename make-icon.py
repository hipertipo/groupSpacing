import os
import groupSpacingLib
from hTools3.objects.hproject import hProject

p = hProject('/_fonts/Jornalistica/Jornalistica Roman')
f1 = OpenFont(p.fonts['91'], showInterface=False)
f2 = OpenFont(p.fonts['55'], showInterface=False)

c1 = 0,
c2 = 1, 0, 0
a = 0.3
s = 'right'
factor = 0.4
S = 0.65

g = RGlyph()
g.interpolate(factor, f1['n'], f2['n'])

siblings = 'nhmlidu' # groupSpacingLib.getSiblings(f1['n'], s)
print(''.join(siblings))

size(512, 512)

save()
stroke(*c2)
strokeWidth(20)
xPos = width() - 30
m = 20
line(
    (xPos, m),
    (xPos, height() - m)
)
restore()

translate(155, 30)
scale(S)

fill(*(c1 + (a,)))
for gName in siblings:
    gs = RGlyph()
    gs.interpolate(factor, f1[gName], f2[gName])
    save()
    d = g.width - gs.width
    translate(d, 0)
    drawGlyph(gs)
    restore()

folder = os.getcwd()
imgPath = os.path.join(folder, 'GroupSpacingMechanicIcon.png')
saveImage(imgPath)

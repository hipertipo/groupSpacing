from importlib import reload
import groupSpacingDialog
reload(groupSpacingDialog)

from mojo.roboFont import OpenWindow
from groupSpacingDialog import GroupSpacingWindow

OpenWindow(GroupSpacingWindow)

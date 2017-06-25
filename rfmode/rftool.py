'''
Copyright (C) 2017 Taylor University, CG Cookie

Created by Dr. Jon Denning and Spring 2015 COS 424 class

Some code copied from CG Cookie Retopoflow project
https://github.com/CGCookie/retopoflow

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

import sys
import math
import os
import time
from abc import ABCMeta, abstractmethod

import bpy
import bgl
from bpy.types import Operator
from bpy.types import SpaceView3D
from bpy_extras.view3d_utils import location_3d_to_region_2d, region_2d_to_vector_3d
from bpy_extras.view3d_utils import region_2d_to_location_3d, region_2d_to_origin_3d
from mathutils import Vector, Matrix, Euler

from ..lib.classes.textbox.textbox import TextBox
from .. import key_maps
from ..lib import common_utilities
from ..lib.common_utilities import print_exception, showErrorMessage
from ..common.registerclasses import RegisterClasses
from .rfwidget import RFWidgetDefault


class RFTool(metaclass=RegisterClasses):
    @staticmethod
    def get_toolset(rfcontext):
        toolset = { rftool:rftool(rfcontext) for rftool in RFTool }     # create instances of each tool
        for tool in toolset.values(): tool.init()                       # init each tool
        return toolset
    
    ''' a base class for all RetopoFlow Tools '''
    def __init__(self, rfcontext):
        self.FSM = {}
        self.init_tool()
        self.FSM['main'] = self.modal_main
        self.mode = 'main'
        self.rfcontext = rfcontext
    
    ''' Called when RetopoFlow plugin is '''
    def init_tool(self): pass
    
    @abstractmethod
    def init(self):
        ''' Called when RetopoFlow is started, but not necessarily when the tool is used '''
        pass
    
    @abstractmethod
    def start(self):
        ''' Called the tool is being switched into. Returns initial state '''
        return None
    
    def rfwidget(self):
        ''' Returns type of cursor to display '''
        return RFWidgetDefault
    
    @abstractmethod
    def modal_main(self): pass
    
    def draw_postview(self): pass
    def draw_postpixel(self): pass
    
    def modal(self):
        (nmode,handled) = self.FSM[self.mode]()
        if nmode: self.mode = nmode
        return handled



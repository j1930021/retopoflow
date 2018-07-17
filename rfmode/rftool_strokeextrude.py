'''
Copyright (C) 2018 CG Cookie
http://cgcookie.com
hello@cgcookie.com

Created by Jonathan Denning, Jonathan Williamson

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

import bgl
import bpy
import math
from mathutils import Vector, Matrix
from mathutils.geometry import intersect_point_tri_2d

from .rftool import RFTool

from ..common.debug import dprint
from ..common.profiler import profiler
from ..common.logger import Logger
from ..common.maths import Point,Point2D,Vec2D,Vec,clamp,Accel2D,Direction
from ..common.bezier import CubicBezierSpline, CubicBezier
from ..common.shaders import circleShader, edgeShortenShader, arrowShader
from ..common.utils import iter_pairs, iter_running_sum
from ..common.ui import (
    UI_Image, UI_IntValue, UI_BoolValue,
    UI_Button, UI_Label,
    UI_Container, UI_EqualContainer
    )
from ..keymaps import default_rf_keymaps
from ..options import options
from ..help import help_strokeextrude

from .rftool_strokeextrude_utils import (
    process_stroke_filter, process_stroke_source,
    find_edge_strips, get_strip_verts,
    restroke,
)



@RFTool.action_call('strokeextrude tool')
class RFTool_StrokeExtrude(RFTool):
    def init(self):
        # self.FSM['handle'] = self.modal_handle
        self.FSM['move']   = self.modal_move
        # self.FSM['rotate'] = self.modal_rotate
        # self.FSM['scale']  = self.modal_scale
        self.FSM['select'] = self.modal_select
        self.FSM['selectadd/deselect'] = self.modal_selectadd_deselect

    def name(self): return "StrokeExtrude"
    def icon(self): return "rf_strokeextrude_icon"
    def description(self): return 'Extrude selection to a stroke!'
    def helptext(self): return help_strokeextrude
    def get_label(self): return 'StrokeExtrude (%s)' % ','.join(default_rf_keymaps['strokeextrude tool'])
    def get_tooltip(self): return 'StrokeExtrude (%s)' % ','.join(default_rf_keymaps['strokeextrude tool'])

    def start(self):
        self.mode = 'main'
        self.rfwidget.set_widget('stroke', color=(0.7, 0.7, 0.7))
        self.rfwidget.set_stroke_callback(self.stroke)
        self.strip_crosses = None
        self.update()

    def get_ui_icon(self):
        self.ui_icon = UI_Image('strokeextrude_32.png')
        self.ui_icon.set_size(16, 16)
        return self.ui_icon

    def get_ui_options(self):
        def get_crosses():
            return getattr(self, 'strip_crosses', None) or 0
        def set_crosses(v):
            v = max(1, int(v))
            if self.strip_crosses == v: return
            self.strip_crosses = v
            self.extrude_strip()
        self.ui_count = UI_IntValue('Crosses', get_crosses, set_crosses)
        return [
            self.ui_count
        ]

    @profiler.profile
    def update(self):
        self.ui_count.visible = self.strip_crosses is not None

    @profiler.profile
    def modal_main(self):
        Point_to_Point2D = self.rfcontext.Point_to_Point2D
        mouse = self.rfcontext.actions.mouse

        self.vis_accel = self.rfcontext.get_vis_accel()

        self.rfwidget.set_widget('stroke')

        if self.rfcontext.actions.pressed('select'):
            self.rfcontext.undo_push('select')
            self.rfcontext.deselect_all()
            return 'select'

        if self.rfcontext.actions.pressed('select add'):
            edge, _ = self.rfcontext.accel_nearest2D_edge()
            if not edge: return
            if edge.select:
                self.mousedown = self.rfcontext.actions.mouse
                return 'selectadd/deselect'
            return 'select'

        if self.rfcontext.actions.pressed('action'):
            pass
            # self.rfcontext.undo_push('select then grab')
            # face = self.rfcontext.accel_nearest2D_face()
            # if not face:
            #     self.rfcontext.deselect_all()
            #     return
            # self.rfcontext.select(face)
            # return self.prep_move()

        if self.rfcontext.actions.pressed('increase count'):
            if self.strip_crosses is not None:
                self.strip_crosses += 1
                self.extrude_strip()
        if self.rfcontext.actions.pressed('decrease count'):
            if self.strip_crosses is not None and self.strip_crosses > 1:
                self.strip_crosses -= 1
                self.extrude_strip()

        if self.rfcontext.actions.pressed('grab'):
            return self.prep_move()

    def stroke(self):
        # called when artist finishes a stroke
        stroke = list(self.rfwidget.stroke2D)
        # filter stroke down where each pt is at least 1px away to eliminate local wiggling
        stroke = process_stroke_filter(stroke)
        stroke = process_stroke_source(stroke, self.rfcontext.raycast_sources_Point2D, self.rfcontext.is_point_on_mirrored_side)

        # TODO: determine if stroke is cyclic
        cyclic = False

        if not cyclic:
            self.strip_stroke = stroke
            self.strip_crosses = None
            self.extrude_strip()


    @RFTool.dirty_when_done
    def extrude_strip(self):
        if self.strip_crosses is not None:
            self.rfcontext.undo_repush('stroke extrude')
        else:
            self.rfcontext.undo_push('stroke extrude')

        Point_to_Point2D = self.rfcontext.Point_to_Point2D
        stroke = self.strip_stroke

        # get selected edges that we can extrude
        edges = [e for e in self.rfcontext.get_selected_edges() if not e.is_manifold]

        s0, s1 = stroke[0], stroke[-1]
        sd = s1 - s0
        # find best strip
        best, best_score = None, None
        for strip in find_edge_strips(edges):
            verts = get_strip_verts(strip)
            p0, p1 = Point_to_Point2D(verts[0].co), Point_to_Point2D(verts[1].co)
            pd = p1 - p0
            dot = pd.x * sd.x + pd.y * sd.y
            if dot < 0:
                strip.reverse()
                verts.reverse()
                p0, p1 = p1, p0
                pd = -pd
                dot = -dot
            score = ((s0 - p0).length + (s1 - p1).length) #* (1 - dot)
            if not best or score < best_score:
                best = strip
                best_score = score
        if not best: return

        # extrude!
        edges = best
        verts = get_strip_verts(edges)
        edge_lens = [
            (Point_to_Point2D(e.verts[0].co) - Point_to_Point2D(e.verts[1].co)).length
            for e in edges
        ]
        strip_len = sum(edge_lens)
        avg_len = strip_len / len(edges)
        per_lens = [l / strip_len for l in edge_lens]
        percentages = [0] + [max(0, min(1, s)) for (w, s) in iter_running_sum(per_lens)]
        nstroke = restroke(stroke, percentages)
        if len(nstroke) != len(verts):
            print(percentages)
            print('nstroke = %d.  verts = %d' % (len(nstroke), len(verts)))
        # average distance between stroke and strip
        p0, p1 = Point_to_Point2D(verts[0].co), Point_to_Point2D(verts[-1].co)
        avg_dist = ((p0 - s0).length + (p1 - s1).length) / 2
        if self.strip_crosses is None:
            self.strip_crosses = max(math.ceil(avg_dist / avg_len), 2) - 1
        crosses = self.strip_crosses + 1
        prev = None
        last = []
        for (v0, p1) in zip(verts, nstroke):
            p0 = Point_to_Point2D(v0.co)
            cur = [v0] + [self.rfcontext.new2D_vert_point(p0 + (p1-p0) * (c / (crosses-1))) for c in range(1, crosses)]
            last.append(cur[-1])
            if prev:
                for i in range(crosses-1):
                    self.rfcontext.new_face([prev[i+0], cur[i+0], cur[i+1], prev[i+1]])
            prev = cur
        nedges = [v0.shared_edge(v1) for (v0, v1) in iter_pairs(last, wrap=False)]
        self.rfcontext.select(nedges)

    @profiler.profile
    def modal_selectadd_deselect(self):
        if not self.rfcontext.actions.using(['select','select add']):
            self.rfcontext.undo_push('deselect')
            edge,_ = self.rfcontext.accel_nearest2D_edge()
            if edge and edge.select: self.rfcontext.deselect(edge)
            return 'main'
        delta = Vec2D(self.rfcontext.actions.mouse - self.mousedown)
        if delta.length > self.drawing.scale(5):
            self.rfcontext.undo_push('select add')
            return 'select'

    @profiler.profile
    def modal_select(self):
        if not self.rfcontext.actions.using(['select','select add']):
            return 'main'
        edge,_ = self.rfcontext.accel_nearest2D_edge(max_dist=10)
        if not edge or edge.select: return
        self.rfcontext.select(edge, supparts=False, only=False)


    @profiler.profile
    def prep_move(self, bmfaces=None):
        if not bmfaces: bmfaces = self.rfcontext.get_selected_faces()
        if not bmfaces: return
        bmverts = set(bmv for bmf in bmfaces for bmv in bmf.verts)
        self.bmverts = [(bmv, self.rfcontext.Point_to_Point2D(bmv.co)) for bmv in bmverts]
        self.mousedown = self.rfcontext.actions.mouse
        self.rfwidget.set_widget('default')
        self.rfcontext.undo_push('move grabbed')
        self.move_done_pressed = 'confirm'
        self.move_done_released = None
        self.move_cancelled = 'cancel'
        return 'move'

    @RFTool.dirty_when_done
    @profiler.profile
    def modal_move(self):
        if self.rfcontext.actions.pressed(self.move_done_pressed):
            return 'main'
        if self.rfcontext.actions.released(self.move_done_released):
            return 'main'
        if self.rfcontext.actions.pressed(self.move_cancelled):
            self.rfcontext.undo_cancel()
            return 'main'

        delta = Vec2D(self.rfcontext.actions.mouse - self.mousedown)
        set2D_vert = self.rfcontext.set2D_vert
        for bmv,xy in self.bmverts:
            set2D_vert(bmv, xy + delta)
        self.rfcontext.update_verts_faces(v for v,_ in self.bmverts)
        self.update()

    def draw_postview(self):
        pass


    def draw_postpixel(self):
        pass



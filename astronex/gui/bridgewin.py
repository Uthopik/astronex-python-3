# -*- coding: utf-8 -*-
import cairo
from copy import copy
from math import pi as PI

from gi.repository import Gtk, Gdk, Pango, PangoCairo

from astronex.drawing.coredraw import CoreMixin
from astronex.drawing.biograph import BioMixin
from astronex.drawing.dispatcher import DrawMixin, AspectManager
from astronex.drawing.roundedcharts import Basic_Chart, RadixChart, NodalChart


def _boss():
    from astronex.boss import boss
    return boss


def _curr():
    return _boss().get_state()


class BridgePEWindow(Gtk.Window):
    def __init__(self, parent):
        self.parnt = parent
        self.get_AP_DEG = parent.boss.da.drawer.get_AP_DEG
        Gtk.Window.__init__(self)
        self.set_type_hint(Gdk.WindowTypeHint.DIALOG)
        self.set_transient_for(parent)
        self.set_destroy_with_parent(True)
        self.set_title(_("PE Puente"))
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect('destroy', self.cb_exit, parent)
        self.connect('button-press-event', self.clicked)

        accel_group = Gtk.AccelGroup()
        accel_group.connect(Gdk.KEY_Escape, 0, Gtk.AccelFlags.LOCKED, self.escape)
        self.add_accel_group(accel_group)

        bridge = BridgeArea(parent.boss, self.get_AP_DEG)
        bridge.set_size_request(450, 450)
        frame = Gtk.Frame()
        frame.add(bridge)
        self.add(frame)
        self.sda = bridge
        # Posicionar ABAJO-DERECHA del area de trabajo del monitor primario (no
        # con Gdk.Screen.get_width, obsoleto y erroneo en multimonitor/HiDPI).
        # El WM puede recentrar los dialogs transient al mapear, asi que se
        # re-fuerza la posicion en 'realize' (Errores2 #6). La ventana se deja
        # DECORADA (con barra de titulo) para que el usuario pueda moverla; el
        # click sigue alternando la decoracion si se quiere un aspecto limpio.
        ax, ay, aw, ah = self._workarea()
        margin = 10
        self._target_pos = (ax + aw - 450 - margin, ay + ah - 450 - margin)
        self.set_position(Gtk.WindowPosition.NONE)
        self.move(*self._target_pos)
        self.connect('realize', self._on_realize)
        self.show_all()
        self.move(*self._target_pos)

    def _workarea(self):
        display = Gdk.Display.get_default()
        monitor = None
        if hasattr(display, 'get_primary_monitor'):
            monitor = display.get_primary_monitor()
        if monitor is None and hasattr(display, 'get_monitor'):
            monitor = display.get_monitor(0)
        if monitor is not None:
            if hasattr(monitor, 'get_workarea'):
                wa = monitor.get_workarea()
            else:
                wa = monitor.get_geometry()
            return wa.x, wa.y, wa.width, wa.height
        screen = Gdk.Screen.get_default()
        return 0, 0, screen.get_width(), screen.get_height()

    def _on_realize(self, *a):
        self.move(*self._target_pos)

    def exit(self):
        self.destroy()

    def escape(self, a, b, c, d):
        self.destroy()

    def cb_exit(self, e, parent):
        parent.boss.mpanel.toolbar.get_nth_item(6).set_active(False)
        return False

    def clicked(self, w, event):
        w.set_decorated(not w.get_decorated())


alts = ['nat', 'nod']


class BridgeArea(Gtk.DrawingArea):
    pepending = [False, None, None]

    def __init__(self, boss, get_AP_DEG):
        self.boss = boss
        self.opts = boss.opts
        Gtk.DrawingArea.__init__(self)
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.POINTER_MOTION_HINT_MASK |
                        Gdk.EventMask.SCROLL_MASK)
        self.connect("draw", self.dispatch)
        self.connect("scroll-event", self.on_scroll)
        self.drawer = Drawer(boss.opts, self, get_AP_DEG)
        self.ops = ['draw', 'bio']

    def _layout(self, cr, font_str, size):
        layout = PangoCairo.create_layout(cr)
        font = Pango.FontDescription.from_string(font_str)
        font.set_size(int(size * Pango.SCALE))
        layout.set_font_description(font)
        return layout

    def dispatch(self, da, cr):
        curr = _curr()
        self.drawer.pe_zones = self.boss.da.drawer.pe_zones
        alloc = self.get_allocation()
        w = alloc.width
        h = alloc.height
        cr.rectangle(0, 0, w, h)
        cr.clip()
        cr.set_source_rgb(0.98, 1.0, 0.98)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_width(float(self.opts.base))

        chart_one, chart_two = curr.curr_chart, curr.curr_click
        if curr.opmode != 'simple':
            currop = curr.opleft
        else:
            currop = curr.curr_op
        op, alt = currop.split('_')
        currop = '_'.join([self.ops[0], alts[alt == 'nat']])
        chartobject = Basic_Chart(chart_one, chart_two)
        # Aislar el translate() interno de la carta con save/restore en vez de
        # cr.identity_matrix(): al ir ACOPLADO en el layout, identity_matrix
        # descartaria la transformacion base del widget en GTK3 y descolocaria
        # las etiquetas (mismo caso que el preview del Explorador).
        cr.save()
        getattr(self.drawer, currop)(cr, w, h, chartobject)
        cr.restore()
        self.draw_pelabel(cr, w, h)
        self.draw_label(cr, w, h)

    def on_scroll(self, da, event):
        self.ops[0], self.ops[1] = self.ops[1], self.ops[0]
        self.redraw()
        return True

    def redraw(self):
        self.queue_draw()

    def draw_pelabel(self, cr, w, h):
        date = self.drawer.dt
        date = date.__str__().split(' ')[0].split('-')
        date.reverse()
        date = "/".join(date)
        cr.set_source_rgb(0, 0, 0.6)
        layout = self._layout(cr, self.opts.font, 9)
        layout.set_text(date, -1)
        _, logical = layout.get_extents()
        xpos = logical.width / Pango.SCALE
        cr.move_to(w - xpos - 5, 5)
        PangoCairo.show_layout(cr, layout)

    def draw_label(self, cr, w, h):
        curr = _curr()
        chart = curr.curr_chart
        name = "%s %s" % (chart.first, chart.last)
        layout = self._layout(cr, self.opts.font, 9)
        col = (0, 0, 0.4)
        layout.set_text(name, -1)
        _, logical = layout.get_extents()
        xpos = logical.width / Pango.SCALE
        cr.set_source_rgb(*col)
        cr.move_to(w - xpos - 5, h - 15)
        PangoCairo.show_layout(cr, layout)


R_ASP = 0.435
MAGICK_FONTSCALE = 0.0012
ruler = [0.9, 0.5]


class Drawer(CoreMixin, BioMixin):
    asplet = ('1', '2', '3', '4', '5', '6', '7', '6', '5', '4', '3', '2')

    def __init__(self, opts, surface, get_AP_DEG):
        self.opts = opts
        self.surface = surface
        self.get_AP_DEG = get_AP_DEG
        self.dt = None
        self.aspmanager = AspectManager(_boss(), self.get_gw, self.get_uni, self.get_nw,
                                        DrawMixin.planetmanager, opts.zodiac.aspcolors, opts.base)
        CoreMixin.__init__(self, opts.zodiac, surface)
        BioMixin.__init__(self, opts.zodiac)
        self.rightdraw = False
        self.pe_zones = False

    def make_crown(self, cr, radius, chartob):
        if self.pe_zones:
            self.d_pe_zones(cr, radius, chartob)
        self.d_radial_lines(cr, radius, chartob)
        self.make_all_rulers(cr, radius, chartob)
        self.draw_signs(cr, radius, chartob)
        self.draw_planets(cr, radius, chartob)
        self.make_plines(cr, radius, chartob, 'EXT')
        self.draw_cusps(cr, radius, chartob)
        self.d_year_lines(cr, radius, chartob)
        self.d_golden_points(cr, radius, chartob)
        self.d_cross_points(cr, radius, chartob)
        self.draw_ap_aspects(cr, radius * R_ASP, chartob, self.aspmanager, self.get_AP(chartob))
        self.aspmanager.manage_aspects(cr, radius * R_ASP, chartob.get_planets())
        self.make_plines(cr, radius, chartob, 'INN')
        self.d_inner_circles(cr, radius)

    def draw_nat(self, cr, width, height, chartob):
        chartob.__class__ = RadixChart
        cx, cy = width / 2, height / 2
        radius = min(cx, cy)
        cr.translate(cx, cy)
        self.make_crown(cr, radius, chartob)

    def draw_nod(self, cr, width, height, chartob=None):
        chartob.__class__ = NodalChart
        chartob.name = 'nodal'
        cx, cy = width / 2, height / 2
        radius = min(cx, cy)
        cr.translate(cx, cy)
        self.make_crown(cr, radius, chartob)

    def get_AP(self, chartob):
        curr = _curr()
        chart = chartob.chart
        dt = curr.date.dt
        cycles = chart.get_cycles(dt)
        dt = chartob.when_angle(cycles, self.get_AP_DEG(), chart)
        self.dt = dt
        pe = chart.which_degree_today(dt, cycles, chartob.name)
        return pe

    def get_gw(self):
        return False

    def get_uni(self):
        return True

    def get_nw(self, f=None):
        return []

    def get_bio_AP(self, chartob):
        curr = _curr()
        chart = chartob.chart
        dt = curr.date.dt
        cycles = chart.get_cycles(dt)
        dt = chartob.when_angle(cycles, self.get_AP_DEG(), chart)
        self.dt = dt
        return dt

    def bio_nat(self, cr, w, h, chartob):
        chartob.__class__ = RadixChart
        self.draw_bio(cr, w, h, chartob)

    def bio_nod(self, cr, w, h, chartob):
        chartob.__class__ = NodalChart
        chartob.name = 'nodal'
        self.draw_bio(cr, w, h, chartob)

    def draw_bio(self, cr, width, height, chartob):
        curr = _curr()
        global ruler
        cr.set_line_width(0.5)
        self.minim = min(width, height)
        self.hoff = hoff = width * 0.125
        self.gridw = hoff * 6
        self.hroff = hoff + self.gridw
        self.voff = voff = height * 0.2

        self.chart = chart = chartob.chart
        cp = chart.calc_cross_points()
        cph = chart.which_house(cp)
        self.sizes = chartob.get_sizes()

        self.get_AP(chartob)
        dt = self.dt
        dt = dt.combine(dt.date(), dt.time())
        bh, tfrac = chart.which_house_today(dt)
        ruler[0] = (hoff + self.gridw * tfrac) / width

        htimes = chartob.get_house_age_prog(bh)
        self.htimes = htimes

        cycles = chart.get_cycles(curr.date.dt)
        self.house_t = chart.house_time_lapsus(bh, cycles)
        layout = PangoCairo.create_layout(cr)
        font = Pango.FontDescription.from_string(self.opts.font)
        font.set_size(int(14 * Pango.SCALE * self.minim * MAGICK_FONTSCALE))
        layout.set_font_description(font)

        self.d_vert_lines(cr)
        self.d_house_number(cr, layout, bh)
        self.d_years_rule(cr, layout, htimes[0])
        if chartob.name == 'nodal':
            self.d_nodal_signbar(cr, layout, bh, chartob)
        else:
            self.d_signbar(cr, layout, bh, chartob)

        self.d_ruler(cr, width, height, voff, chartob.pe_col)

        self.baselines = []
        self.d_baselines(cr, layout)
        if self.pe_zones:
            self.d_pe_zone(cr, bh, chartob)
        self.d_midpoint_line(cr, chartob)
        mids = [t for t in htimes if t['cl'] == 'mid']
        if mids:
            self.d_midplans(cr, layout, mids)

        self.intensity = [0] * 72
        self.d_prev_house(cr, layout, bh, chartob)
        self.d_this_house(cr, layout, bh, chartob.name)
        self.d_follow_house(cr, layout, bh, chartob)

        self.d_intensity(cr, chartob)
        if bh in [cph, (cph + 6) % 12]:
            if bh != cph:
                cp = (cp + 180) % 360
            self.d_cross_point(cr, bh, cp, chartob)

    def d_ruler(self, cr, width, height, voff, pe_col):
        cr.set_source_rgba(*(list(pe_col) + [0.5]))
        cr.arc(width * ruler[0], height * ruler[1], 5, 0, 180 * PI)
        cr.fill()
        cr.move_to(width * ruler[0], voff)
        cr.line_to(width * ruler[0], voff + voff * 3)
        cr.stroke()

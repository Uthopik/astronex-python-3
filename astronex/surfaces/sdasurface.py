# -*- coding: utf-8 -*-
import cairo
import math
from math import pi as PI
from collections import deque
from copy import copy
from datetime import datetime

from gi.repository import Gtk, Gdk, Pango, PangoCairo

from astronex.drawing.dispatcher import DrawMixin
from astronex.drawing.diagrams import DiagramMixin
from astronex.drawing.biograph import _bio
from astronex.utils import parsestrtime


def _boss():
    from astronex.boss import boss
    return boss


def _curr():
    return _boss().get_state()


RAD = PI / 180


class DrawDiagram(Gtk.DrawingArea):
    opdia = deque(['dyn_bars', 'dyn_energy', 'dyn_differences', 'dyn_houses', 'dyn_signs'])

    def __init__(self, boss):
        self.boss = boss
        self.opts = boss.opts
        Gtk.DrawingArea.__init__(self)
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.POINTER_MOTION_HINT_MASK |
                        Gdk.EventMask.SCROLL_MASK)
        self.connect("draw", self.dispatch)
        self.connect("button-press-event", self.on_diada_clicked)
        self.connect("scroll-event", self.on_scroll)
        self.drawer = DiagramMixin(boss.opts.zodiac)

    def dispatch(self, da, cr):
        alloc = self.get_allocation()
        w = alloc.width
        h = alloc.height
        cr.rectangle(0, 0, w, h)
        cr.clip()
        cr.set_source_rgb(1.0, 1.0, 0.95)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_width(float(self.opts.base))

        getattr(self.drawer, self.opdia[0])(cr, w, h)
        return True

    def on_scroll(self, da, event):
        if event.direction == Gdk.ScrollDirection.UP:
            self.opdia.rotate(1)
        elif event.direction == Gdk.ScrollDirection.DOWN:
            self.opdia.rotate(-1)
        elif event.direction == Gdk.ScrollDirection.SMOOTH:
            ok, dx, dy = event.get_scroll_deltas()
            if not ok or dy == 0:
                return True
            self.opdia.rotate(1 if dy < 0 else -1)
        else:
            return True
        self.redraw()
        return True

    def on_diada_clicked(self, hs, event):
        if event.type == Gdk.EventType._2BUTTON_PRESS and event.button == 1:
            _boss().mpanel.toolbar.get_nth_item(5).set_active(False)
        return True

    def redraw(self):
        self.queue_draw()


crcol = ['card', 'fix', 'mut']
crosscolsalpha = [(0.7, 0, 0.2, 0.7), (0.1, 0.1, 0.6, 0.7), (0, 0.6, 0.1, 0.7)]
crosscols = [(0.7, 0, 0.2), (0.1, 0.1, 0.6), (0, 0.6, 0.1)]
_h = -1
prev_chart = None


class HouseSelector(Gtk.DrawingArea):
    def __init__(self, boss):
        global prev_chart
        self.boss = boss
        self.opts = boss.opts
        Gtk.DrawingArea.__init__(self)
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.POINTER_MOTION_HINT_MASK |
                        Gdk.EventMask.SCROLL_MASK)
        self.connect("draw", self.dispatch)
        self.connect("button-press-event", self.on_hs_clicked)
        self.connect("scroll-event", self.on_scroll)
        try:
            curr = _curr()
            prev_chart = curr.curr_chart, curr.curr_chart.first, curr.curr_op
        except AttributeError:
            pass

    def set_house_from_date(self, dt):
        global _h
        curr = _curr()
        _bio_h, frac = curr.curr_chart.which_house_today(dt)
        _h = _bio_h
        self.queue_draw()
        parent = self.get_parent().get_parent()
        parent.drawer.set_bio_from_date(_bio_h, frac)

    def on_hs_clicked(self, hs, event):
        global _h
        curr = _curr()
        if curr.curr_chart == curr.now:
            return True
        x, y = event.x, event.y
        parent = self.get_parent().get_parent()
        if event.type == Gdk.EventType._2BUTTON_PRESS and event.button == 1:
            parent.panel.nowbut.emit('clicked')
            _h = -1
            self.queue_draw()
        elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            alloc = hs.get_allocation()
            w = alloc.width / 2
            h = alloc.height / 2
            deg = math.degrees(math.atan2(y - h, x - w))
            _h = int(math.ceil(5 - (deg / 30)))
            self.queue_draw()
            parent.drawer.set_bio(_h, None)
        return True

    def dispatch(self, da, cr):
        global _h, prev_chart
        curr = _curr()
        alloc = self.get_allocation()
        w = alloc.width
        h = alloc.height
        cr.rectangle(0, 0, w, h)
        cr.clip()
        cr.set_source_rgb(1.0, 0.9, 0.65)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_width(float(self.opts.base))

        cr.translate(w / 2, h / 2)
        r = min(w / 2, h / 2)
        ro = r * 0.8
        ri = r * 0.4
        rm = r * 0.6
        cr.set_source_rgb(0, 0, 0.8)
        cr.arc(0, 0, r * 0.08, 0, 180 * PI)
        cr.fill()
        pointcol = (0.9, 0.8, 0.6)
        cr.set_source_rgb(*pointcol)
        cr.arc(0, 0, r * 0.03, 0, 180 * PI)
        cr.fill()
        for ang in range(0, 360, 30):
            ix = (ang // 30) % 3
            a = 180 - ang
            cr.set_source_rgba(*crosscols[ix])
            cr.move_to(ri * math.cos(a * RAD), ri * math.sin(a * RAD))
            cr.line_to(ro * math.cos(a * RAD), ro * math.sin(a * RAD))
            cr.arc_negative(0, 0, ro, a * RAD, (a - 30) * RAD)
            cr.line_to(ri * math.cos((a - 30) * RAD), ri * math.sin((a - 30) * RAD))
            cr.arc(0, 0, ri, (a - 30) * RAD, a * RAD)
            cr.fill()

        this_chart = curr.curr_chart, curr.curr_chart.first, curr.curr_op
        if prev_chart is not None and this_chart[1] != prev_chart[1]:
            _h = -1

        if this_chart != prev_chart:
            prev_chart = this_chart

        if _h < 0:
            _h, _ = curr.curr_chart.which_house_today(datetime.now())

        cr.set_source_rgb(*pointcol)
        x = rm * math.cos((165 - _h * 30) * RAD)
        y = rm * math.sin((165 - _h * 30) * RAD)
        cr.move_to(0, 0)
        cr.line_to(x, y)
        cr.stroke()
        cr.arc(x, y, 5, 0, 180 * PI)
        cr.fill()
        return True

    def on_scroll(self, hs, event):
        global _h
        curr = _curr()
        if curr.curr_chart == curr.now:
            return True
        if event.direction == Gdk.ScrollDirection.UP:
            _h = (_h - 1) % 12
        elif event.direction == Gdk.ScrollDirection.DOWN:
            _h = (_h + 1) % 12
        elif event.direction == Gdk.ScrollDirection.SMOOTH:
            ok, dx, dy = event.get_scroll_deltas()
            if not ok or dy == 0:
                return True
            _h = (_h + (-1 if dy < 0 else 1)) % 12
        else:
            return True
        self.queue_draw()
        parent = self.get_parent().get_parent()
        parent.drawer.set_bio(_h, None)
        return True

    def house_updown(self, amount):
        global _h
        _h = (_h + amount) % 12
        self.queue_draw()
        parent = self.get_parent().get_parent()
        parent.drawer.set_bio(_h, None)

    def redraw(self):
        self.queue_draw()


opcharts = ['draw_nat', 'draw_house',
            'draw_nod', 'draw_soul', 'draw_dharma', 'draw_ur_nodal', 'draw_local', 'draw_prof', 'draw_int', 'draw_single', 'draw_radsoul']
opclicks = ['click_hh', 'click_nn', 'click_hn', 'click_nh', 'click_ss', 'click_rr', 'click_rs', 'click_sn', 'subject_click']
opdia = ['dyn_bars', 'dyn_energy', 'dyn_differences', 'dyn_houses', 'dyn_signs']
opbio = ['bio_nat', 'bio_nod', 'bio_soul', 'bio_dharma']
optrans = ['draw_transits', 'sec_prog', 'solar_rev']
opcoup = ['ascent_star', 'wundersensi_star', 'polar_star', 'crown_comp', 'paarwabe_plot', 'comp_pe']
tradtrans = {'draw_transits': _('Transitos'), 'sec_prog': _('Progresion secundaria'), 'solar_rev': _('Revolucion solar')}
initmenu = (_('Congelar'), _('Permutar'), _('Cartas'), 'Clics', _('DDiagramas'), _('Biografias'), _('Parejas'), _('Transitos'))


class DrawAux(Gtk.DrawingArea):
    pepending = [False, None, None]

    def __init__(self, boss, chart=None):
        self.boss = boss
        self.opts = boss.opts
        self.opcharts = deque(opcharts)
        self.opclicks = deque(opclicks)
        self.opdia = deque(opdia)
        self.opbio = deque(opbio)
        self.opcoup = deque(opcoup)
        self.optrans = deque(optrans)
        self.opaux = self.opcharts
        Gtk.DrawingArea.__init__(self)
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.POINTER_MOTION_HINT_MASK |
                        Gdk.EventMask.SCROLL_MASK)
        self.connect("draw", self.dispatch)
        self.connect("button-press-event", self.on_da_clicked)
        self.connect("scroll-event", self.on_scroll)
        self.drawer = DrawMixin(boss.opts, self)
        self.menu = Gtk.Menu()
        for buf in initmenu:
            menu_item = Gtk.MenuItem(label=buf)
            self.menu.append(menu_item)
            menu_item.connect("activate", self.on_menuitem_activate)
            menu_item.show()
        sep_item = Gtk.SeparatorMenuItem()
        self.menu.insert(sep_item, 2)
        sep_item.show()
        curr = _curr()
        if chart:
            self.cache = [copy(chart), copy(curr.curr_click)]
            self.frozen = True
        else:
            self.cache = [copy(curr.curr_chart), copy(curr.curr_click)]
            self.frozen = False
        self.permuted = False

    def _layout_with_font(self, cr, font_str, size):
        layout = PangoCairo.create_layout(cr)
        font = Pango.FontDescription.from_string(font_str)
        font.set_size(int(size * Pango.SCALE))
        layout.set_font_description(font)
        return layout

    def dispatch(self, da, cr):
        curr = _curr()
        alloc = self.get_allocation()
        w = alloc.width
        h = alloc.height
        cr.rectangle(0, 0, w, h)
        cr.clip()
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_width(float(self.opts.base))

        if not self.frozen:
            self.cache = [copy(curr.curr_chart), copy(curr.curr_click)]
            if self.permuted:
                self.cache[0], self.cache[1] = self.cache[1], self.cache[0]
        self.drawer.dispatch_simple(cr, w, h, self.opaux[0], self.cache[0], self.cache[1])
        if self.opaux == self.optrans or self.cache[0].first == _("Momento actual"):
            self.d_now_date(cr, w, h)
        if self.pepending[0]:
            self.draw_pelabel(cr, w, h)
            self.pepending = [False, None, None]
        self.draw_label(cr, w, h)
        return False

    def on_scroll(self, da, event):
        if event.direction == Gdk.ScrollDirection.UP:
            self.opaux.rotate(1)
        elif event.direction == Gdk.ScrollDirection.DOWN:
            self.opaux.rotate(-1)
        elif event.direction == Gdk.ScrollDirection.SMOOTH:
            ok, dx, dy = event.get_scroll_deltas()
            if not ok or dy == 0:
                return True
            self.opaux.rotate(1 if dy < 0 else -1)
        else:
            return True
        self.redraw()
        return True

    def redraw(self):
        self.queue_draw()

    def popup_menu(self):
        self.menu.popup_at_pointer(None)

    def on_da_clicked(self, da, event):
        curr = _curr()
        x, y = event.x, event.y
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self.menu.popup_at_pointer(event)
            return True
        if event.type == Gdk.EventType._2BUTTON_PRESS and event.button == 1:
            if self.opaux == self.opbio:
                return False
            if self.opaux == self.opcharts:
                rad = list(self.opaux).index('draw_nat')
            elif self.opaux == self.opclicks:
                rad = list(self.opaux).index('click_hh')
            elif self.opaux == self.opdia:
                rad = list(self.opaux).index('dyn_bars')
            else:
                rad = 0
            self.opaux.rotate(-rad)
            self.redraw()
            return True
        elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            if self.opaux == self.opbio:
                return False
            if not self.drawer.get_showAP() or self.opaux != self.opcharts:
                return True
            alloc = da.get_allocation()
            w = alloc.width / 2
            h = alloc.height / 2
            deg = math.degrees(math.atan2(y - h, x - w))
            for_ch = ['chart', 'click'][self.permuted]
            self.drawer.set_AP(deg, self.opaux[0], for_ch)
            self.boss.da.redraw()
            self.boss.da.redraw_auxwins()
            if curr.curr_op in ['bio_nat', 'bio_nod', 'bio_soul']:
                dt = curr.date.dt
                dt = datetime.combine(dt.date(), dt.time())
                _boss().da.hsel.get_child().set_house_from_date(dt)
            return True

    def on_menuitem_activate(self, menuitem):
        label = menuitem.get_label()
        if label == _('Descongelar'):
            self.frozen = False
            menuitem.set_label(_('Congelar'))
        elif label == _('Congelar'):
            self.frozen = True
            menuitem.set_label(_('Descongelar'))
        elif label == _('Permutar'):
            self.cache[0], self.cache[1] = self.cache[1], self.cache[0]
            self.permuted = not self.permuted
        elif label == 'Clics':
            self.opaux = self.opclicks
        elif label == _('DDiagramas'):
            self.opaux = self.opdia
        elif label == _('Cartas'):
            self.opaux = self.opcharts
        elif label == _('Transitos'):
            self.opaux = self.optrans
        elif label == _('Parejas'):
            self.opaux = self.opcoup
        elif label == _('Biografias'):
            self.opaux = self.opbio
        self.redraw()
        return True

    def draw_label(self, cr, w, h):
        layout = self._layout_with_font(cr, self.opts.font, 9)

        cols = [(0, 0, 0.4), (0.8, 0, 0.1)]
        if self.permuted:
            cols[1], cols[0] = cols[0], cols[1]

        ix = [0, 1][self.opaux in [self.opclicks, self.opcoup]]
        fac = [1, 2][self.opaux == self.opdia or self.opaux == self.opbio or self.opaux[0] == 'comp_pe']
        h = (fac * h / 2) - 15
        if self.opaux[0] == 'comp_pe':
            signfac = 0
        else:
            signfac = -1

        for i in range(ix + 1):
            name = "%s %s" % (self.cache[i].first, self.cache[i].last)
            layout.set_text(name, -1)
            _, logical = layout.get_extents()
            xpos = logical.width / Pango.SCALE
            if ix and not i:
                pos = signfac * (fac * w / 2) + 5
            else:
                pos = (fac * w / 2) - xpos - 5
            cr.set_source_rgb(*cols[i])
            cr.move_to(pos, h)
            PangoCairo.show_layout(cr, layout)

        if self.opaux == self.optrans:
            layout.set_text(tradtrans[self.opaux[0]], -1)
            cr.move_to(5 - w / 2, h)
            PangoCairo.show_layout(cr, layout)

    def d_now_date(self, cr, w, h):
        curr = _curr()
        strdate = curr.charts['now'].date
        date, t = parsestrtime(strdate)
        date = date + " " + t.split(" ")[0]
        cr.set_source_rgb(0, 0, 0.6)
        layout = self._layout_with_font(cr, self.opts.font, 8)
        layout.set_text(date, -1)
        _, logical = layout.get_extents()
        xpos = logical.width / Pango.SCALE
        cr.move_to((w / 2) - xpos - 5, (-h / 2) + 5)
        PangoCairo.show_layout(cr, layout)

    def d_tr_label(self, cr, w, h):
        pass

    def draw_pelabel(self, cr, w, h):
        boss = _boss()
        pe = self.pepending[1]
        sign, deg = divmod(pe, 30)
        mint = int((deg - int(deg)) * 60)
        sign = int(sign)
        deg = int(deg)
        let = self.drawer.zodlet[sign]
        col = boss.opts.zodiac.zod[sign].col
        sign_str = "%s° %s´" % (deg, mint)

        iambio = (self.opaux == self.opbio)
        h = -([1, 0][iambio] * h / 2) + 5
        w = ([1, 2][iambio] * w / 2) - 5

        layout = self._layout_with_font(cr, "Astro-Nex", 9)
        cr.set_source_rgb(*col)
        layout.set_text(let, -1)
        _, logical = layout.get_extents()
        xpos = logical.width / Pango.SCALE
        cr.move_to(w - xpos, h)
        PangoCairo.show_layout(cr, layout)

        cr.set_source_rgb(0, 0, 0.6)
        layout = self._layout_with_font(cr, self.opts.font, 9)
        layout.set_text(sign_str, -1)
        _, logical = layout.get_extents()
        xpos += logical.width / Pango.SCALE
        cr.move_to(w - xpos, h)
        PangoCairo.show_layout(cr, layout)

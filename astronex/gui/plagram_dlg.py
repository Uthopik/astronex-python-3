# -*- coding: utf-8 -*-
import os
import sys
import shlex
import subprocess
from collections import deque

import cairo
import PIL.Image
from gi.repository import Gtk, Gdk, Pango, PangoCairo

from astronex.drawing.dispatcher import PlanetManager
from astronex.drawing.coredraw import CoreMixin
from astronex.drawing.planetogram import PlanetogramMixin
from astronex.drawing.aspects import AspectManager
import astronex.drawing.roundedcharts as roundedcharts
from astronex.drawing.roundedcharts import (
    Basic_Chart, RadixChart, SoulChart, NodalChart, HouseChart, dif
)
from astronex.surfaces.pngsurface import (
    get_export_dialog, ajusta_extension, guardar_imagen
)


def _boss():
    from astronex.boss import boss
    return boss


def _curr():
    return _boss().get_state()


R_ASP = 0.435
RAD = 3.141592653589793 / 180.0
letters = ('d', 'f', 'h', 'j', 'k', 'l', 'g', 'z', 'x', 'c', 'v')
alet = ('1', '2', '3', '4', '5', '6', '7', '6', '5', '4', '3', '2')
PDFH = 845.04685
PDFW = 597.50787  # A4 points


class PlagramWindow(Gtk.Window):
    def __init__(self, parent, chart=None):
        self.boss = parent.boss
        Gtk.Window.__init__(self)
        self.set_type_hint(Gdk.WindowTypeHint.NORMAL)
        self.set_transient_for(parent)
        self.set_title("Planetograma")

        # ESC / X = OCULTAR (no destruir) y reutilizar. Destruir esta ventana en
        # GTK3/WSLg provocaba un segfault que mataba toda la app; al no destruirla
        # nunca durante la sesion se evita el camino de finalizacion que crasheaba.
        # La instancia se retiene en winnex.plagram y se vuelve a mostrar con
        # deiconify()+present() (mismo patron que HelpWindow en quickhelp.py).
        self.connect('key-press-event', self.on_key_press)
        self.connect('delete-event', self.on_delete)

        # Se conserva solo el accel de la tecla Menu (menu contextual).
        accel_group = Gtk.AccelGroup()
        accel_group.connect(Gdk.KEY_Menu, 0, Gtk.AccelFlags.LOCKED, self.popup_menu)
        self.add_accel_group(accel_group)

        self.sda = DrawPlagram(self.boss, chart)
        self.add(self.sda)
        aux_size = int(self.boss.opts.aux_size)
        self.set_default_size(int(aux_size * 1.2), aux_size)
        self.show_all()

    def on_key_press(self, widget, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        return False

    def on_delete(self, widget, event):
        # No destruir: ocultar (return True evita el destroy por defecto).
        self.hide()
        return True

    def popup_menu(self, acgroup, actable, keyval, mod):
        self.sda.popup_menu_at_pointer()


class DrawPlagram(Gtk.DrawingArea):
    def __init__(self, boss, chart=None):
        self.boss = boss
        self.opts = boss.opts
        Gtk.DrawingArea.__init__(self)
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.POINTER_MOTION_HINT_MASK |
                        Gdk.EventMask.SCROLL_MASK |
                        Gdk.EventMask.SMOOTH_SCROLL_MASK)
        self.connect("draw", self.dispatch)
        self.connect("button-press-event", self.on_da_clicked)
        self.connect("button-release-event", self.on_da_clicked)
        self.connect("motion-notify-event", self.on_da_clicked)
        self.connect("scroll-event", self.on_scroll)
        self.drawer = PgMixin(boss, self)
        self.build_menu()
        self.extended = False
        self.zoom = 1.0
        self.do_zoom = False
        self.reset = False
        self.panning = False
        self.pan_x = self.pan_y = 0
        self.zx = self.zy = 0
        self._move_info = {'button': -1, 'click_x': 0, 'click_y': 0}

    def build_menu(self):
        self.menu = Gtk.Menu()
        menu_item = Gtk.MenuItem(label=_('Exportar a imagen'))
        self.menu.append(menu_item)
        menu_item.connect("activate", self.on_menuitem_activate)
        menu_item.show()
        menu_item = Gtk.MenuItem(label=_('Exportar a PDF'))
        self.menu.append(menu_item)
        menu_item.connect("activate", self.on_menuitem_activate)
        menu_item.show()
        sep_item = Gtk.SeparatorMenuItem()
        self.menu.append(sep_item)
        sep_item.show()
        menu_item = Gtk.CheckMenuItem(label=_('Ver puntos de sombra'))
        self.menu.append(menu_item)
        menu_item.connect("toggled", self.on_check_toggled)
        menu_item.set_active(True)
        menu_item.show()
        menu_item = Gtk.CheckMenuItem(label=_('Ver puntos de cambio'))
        self.menu.append(menu_item)
        menu_item.connect("toggled", self.on_check_toggled)
        menu_item.set_active(True)
        menu_item.show()
        menu_item = Gtk.CheckMenuItem(label=_('Ver puntos de cruce'))
        self.menu.append(menu_item)
        menu_item.connect("toggled", self.on_check_toggled)
        menu_item.set_active(True)
        menu_item.show()
        menu_item = Gtk.CheckMenuItem(label=_('Ver lineas personales'))
        self.menu.append(menu_item)
        menu_item.connect("toggled", self.on_check_toggled)
        menu_item.set_active(False)
        menu_item.show()
        menu_item = Gtk.MenuItem(label=_('Commutar anos/edad'))
        self.menu.append(menu_item)
        menu_item.connect("activate", self.on_menuitem_activate)
        menu_item.show()

    def popup_menu_at_pointer(self, event=None):
        if event is not None:
            self.menu.popup_at_pointer(event)
        else:
            self.menu.popup_at_pointer(None)

    def on_menuitem_activate(self, menuitem):
        label = menuitem.get_label()
        if label == _('Exportar a imagen'):
            self.png_export()
        elif label == _('Commutar anos/edad'):
            self.drawer.useagecircle = not self.drawer.useagecircle
        elif label == _('Exportar a PDF'):
            self.pdf_export()
        self.redraw()

    def on_check_toggled(self, menuitem):
        label = menuitem.get_label()
        active = menuitem.get_active()
        if label == _('Ver puntos de sombra'):
            self.drawer.shadow = active
        elif label == _('Ver lineas personales'):
            self.drawer.personlines = active
        elif label == _('Ver puntos de cambio'):
            self.drawer.turnpoints = active
        elif label == _('Ver puntos de cruce'):
            self.drawer.crosspoints = active
        self.redraw()

    def on_da_clicked(self, da, event):
        info = self._move_info

        if event.type == Gdk.EventType._2BUTTON_PRESS and event.button == 1:
            self.extended = not self.extended
            self.reset = True
            self.redraw()
        elif event.type == Gdk.EventType.BUTTON_PRESS:
            if event.button == 3:
                self.menu.popup_at_pointer(event)
                return True
            elif event.button == 1:
                if info['button'] < 0:
                    info['button'] = event.button
                    info['click_x'] = event.x
                    info['click_y'] = event.y
                    self.panning = True
        elif event.type == Gdk.EventType.BUTTON_RELEASE:
            if info['button'] < 0:
                return True
            if info['button'] == event.button:
                info['button'] = -1
                self.panning = False
        elif event.type == Gdk.EventType.MOTION_NOTIFY:
            if info['button'] < 0:
                return False
            x = event.x - info['click_x']
            y = event.y - info['click_y']
            self.pan_x, self.pan_y = x, y
            self.redraw()

    def on_scroll(self, da, event):
        if event.direction == Gdk.ScrollDirection.UP:
            self.zoom *= 1.2
        elif event.direction == Gdk.ScrollDirection.DOWN:
            self.zoom = self.zoom / 1.2 if self.zoom >= 1.2 else 1.0
        elif event.direction == Gdk.ScrollDirection.SMOOTH:
            ok, dx, dy = event.get_scroll_deltas()
            if not ok or dy == 0:
                return True
            if dy < 0:
                self.zoom *= 1.2
            else:
                self.zoom = self.zoom / 1.2 if self.zoom >= 1.2 else 1.0
        else:
            return True
        if self.zoom == 1.0:
            self.do_zoom = False
        else:
            self.do_zoom = True
        self.zx = event.x
        self.zy = event.y
        self.redraw()
        return True

    def dispatch(self, da, cr):
        alloc = self.get_allocation()
        w = alloc.width
        h = alloc.height
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        # Guardar la transformacion base del widget ANTES del zoom/paneo: el
        # nombre y el primer aspecto se pintan siempre respecto a ella para que
        # no se deslicen fuera del area al hacer zoom (ver dispatch_simple).
        self.drawer.base_matrix = cr.get_matrix()
        if self.reset:
            self.reset = False
        else:
            if self.do_zoom:
                z = self.zoom
                cr.scale(z, z)
                ux, uy = cr.user_to_device(self.zx, self.zy)
                cr.translate(self.zx - ux, self.zy - uy)
        if self.panning:
            cr.translate(*cr.device_to_user_distance(self.pan_x, self.pan_y))
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_width(float(self.opts.base))
        self.drawer.dispatch_simple(cr, w, h)
        return False

    def redraw(self):
        self.queue_draw()

    def png_export(self):
        dialog = get_export_dialog(pg=True)
        filename = None
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.chooser.get_filename()
        # No destruir (destroy() crashea en GTK3/WSLg): ocultar y reutilizar.
        dialog.hide()
        if not filename:
            return
        filename = ajusta_extension(filename, dialog)

        w = int(self.opts.hsize)
        h = int(self.opts.vsize)
        surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h)
        cr = cairo.Context(surface)
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_width(float(self.opts.base))
        dr = PgMixin(self.boss, self)
        dr.dispatch_simple(cr, w, h)

        buf = bytes(surface.get_data())
        ba = bytearray(buf)
        for i in range(0, len(ba), 4):
            ba[i], ba[i + 2] = ba[i + 2], ba[i]
            ba[i + 3] = buf[i + 3]
        im = PIL.Image.frombuffer("RGBA", (surface.get_width(), surface.get_height()),
                                  bytes(ba), "raw", "RGBA", 0, 1)
        res = int(self.opts.resolution)
        im.info['dpi'] = (res, res)
        guardar_imagen(im, filename)

        viewer = getattr(self.opts, 'pngviewer', None)
        if viewer:
            try:
                subprocess.Popen(shlex.split(viewer) + [filename],
                                 stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL,
                                 start_new_session=True)
            except (OSError, FileNotFoundError):
                pass

    def pdf_export(self):
        dialog = Gtk.FileChooserDialog(
            title=_("Guardar..."),
            parent=None,
            action=Gtk.FileChooserAction.SAVE,
        )
        dialog.add_buttons(_("_Cancelar"), Gtk.ResponseType.CANCEL,
                           _("_Guardar"), Gtk.ResponseType.OK)
        dialog.set_default_response(Gtk.ResponseType.OK)
        filt = Gtk.FileFilter()
        filt.set_name(_("Documento PDF"))
        filt.add_mime_type("application/pdf")
        filt.add_pattern("*.pdf")
        dialog.add_filter(filt)
        curr = _curr()
        name = curr.curr_chart.first + "_pg.pdf"
        dialog.set_current_name(name)
        dialog.set_current_folder(os.path.expanduser("~"))
        dialog.set_do_overwrite_confirmation(True)

        filename = None
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
        # No destruir (destroy() de una toplevel crashea en GTK3/WSLg): ocultar.
        dialog.hide()
        if not filename:
            return

        w = PDFH
        h = PDFW
        surface = cairo.PDFSurface(filename, w, h)
        surface.set_fallback_resolution(300, 300)
        cr = cairo.Context(surface)
        cr.rectangle(0, 0, w, h)
        cr.clip()
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_width(float(self.opts.base))
        dr = PgMixin(self.boss, self)
        dr.dispatch_simple(cr, w, h)
        cr.show_page()
        surface.finish()

        viewer = getattr(self.opts, 'pdfviewer', None)
        if viewer:
            try:
                subprocess.Popen(shlex.split(viewer) + [filename],
                                 stdin=subprocess.DEVNULL,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL,
                                 start_new_session=True)
            except (OSError, FileNotFoundError):
                pass


class PgMixin(CoreMixin, PlanetogramMixin):
    def __init__(self, boss, surface=None):
        self.opts = boss.opts
        self.surface = surface
        self.shadow = True
        self.personlines = False
        self.turnpoints = True
        self.crosspoints = True
        self.useagecircle = False
        self.planetmanager = PlanetManager(self.opts.zodiac)
        # Transformacion base del widget (sin zoom ni paneo) con la que se
        # pintan el nombre y los glifos del primer aspecto. La rellena
        # DrawPlagram.dispatch en cada dibujado; en la exportacion a imagen se
        # queda a None y se usa la matriz del contexto, que ya es la identidad.
        self.base_matrix = None
        roundedcharts.zodiac = self.opts.zodiac
        self.aspmanager = AspectManager(boss, self.get_gw, self.get_uni, self.get_nw,
                                        self.planetmanager, self.opts.zodiac.aspcolors, self.opts.base)
        CoreMixin.__init__(self, self.opts.zodiac, surface)
        PlanetogramMixin.__init__(self, self.opts.zodiac)

    def dispatch_simple(self, cr, w, h):
        curr = _curr()
        ch1, ch2 = curr.curr_chart, curr.curr_click
        chartobject = Basic_Chart(ch1, ch2, self.planetmanager)
        # Aislar los translate() del dibujo de la carta con save/restore en vez
        # de cr.identity_matrix(): en GTK3 identity_matrix descarta la
        # transformacion base del widget y dejaba el nombre y el primer aspecto
        # pegados/cortados a la izquierda (mismo caso ya corregido en
        # chartbrowser.py y bridgewin.py).
        cr.save()
        if not self.surface.extended:
            cr.translate(w / 2.7, h / 2)
            self.draw_planetogram(cr, w * 0.7, h, chartobject)
            cr.translate(w * 0.45, -h / 3.2)
            self.aspmanager.unilat.lw = 0.5 * float(self.aspmanager.unilat.lw)
            self.draw_soul(cr, w / 2.6, h / 2.6, chartobject)
            cr.translate(0, 2 * h / 3.2)
            self.draw_house(cr, w / 2.6, h / 2.6, chartobject)
            cr.translate(0, -1.4 * h / 3.2)
            self.lin_rulers(cr, w / 7, h / 4, chartobject)
            self.aspmanager.unilat.lw /= 0.5
        else:
            cr.translate(w / 2, h / 2)
            self.draw_planetogram(cr, w, h, chartobject)
        cr.restore()
        # El nombre de la carta y los glifos del primer aspecto van CLAVADOS a
        # la esquina del area de dibujo: no deben moverse ni escalar con el
        # zoom/paneo. En el Py2 eso lo conseguia cr.identity_matrix(), que
        # anulaba TODO (traslaciones de la carta + zoom + paneo). Al sustituirlo
        # por save/restore se dejo de anular el zoom, y con la rueda el nombre y
        # el primer aspecto se deslizaban hacia la izquierda hasta salirse del
        # area (x negativa) — el "esta muy pegado a la izquierda" que reporto
        # Elias. Aqui se vuelve a la transformacion base del widget, que es lo
        # que identity_matrix() daba en GTK2 sin descartar la de GTK3.
        cr.save()
        if self.base_matrix is not None:
            cr.set_matrix(self.base_matrix)
        self.draw_label(cr, w, h, chartobject)
        self.plot_cons_plan(cr, h, chartobject)
        cr.restore()

    def get_gw(self):
        return False

    def get_nw(self, filter):
        return None

    def get_uni(self):
        return True

    def lin_rulers(self, cr, w, h, chartob):
        hor_grid = w / 3
        ver_grid = h / 30.0
        cr.save()
        lw = cr.get_line_width()
        cr.set_line_width(0.4 * lw)

        cr.rectangle(hor_grid * 0.9, 0, hor_grid * 0.07, h)
        pat = cairo.LinearGradient(hor_grid, 0, hor_grid, h)
        pat.add_color_stop_rgb(0.0, 0, 0, 1)
        pat.add_color_stop_rgb(0.4, 0, 0.9, 0)
        pat.add_color_stop_rgb(0.6, 1, 0.8, 0)
        pat.add_color_stop_rgb(0.7, 1, 0, 0)
        pat.add_color_stop_rgb(1.0, 0, 0, 1)
        cr.set_source(pat)
        cr.fill()

        for r in [0.92, 1.12]:
            cr.set_source_rgb(0.75, 0.8, 0.9)
            cr.rectangle(2 * hor_grid * r, 0, hor_grid * 0.12, h)
            cr.fill()
            cr.set_source_rgb(0.85, 0.8, 0.96)
            cr.rectangle(2 * hor_grid * r, ver_grid * 2, hor_grid * 0.12, ver_grid * 25)
            cr.fill()
            cr.set_source_rgb(1.0, 0.85, 0.85)
            cr.rectangle(2 * hor_grid * r, ver_grid * 12, hor_grid * 0.12, ver_grid * 10)
            cr.fill()

        cr.set_source_rgb(0.3, 0.3, 0.3)
        for i in range(31):
            if i % 5 == 0:
                cr.set_line_width(0.7 * lw)
            else:
                cr.set_line_width(0.4 * lw)
            cr.move_to(hor_grid * 0.86, i * ver_grid)
            cr.line_to(hor_grid, i * ver_grid)
            cr.stroke()
            cr.move_to(2 * hor_grid * 0.92, i * ver_grid)
            cr.line_to(2 * hor_grid * 0.98, i * ver_grid)
            cr.stroke()
            cr.move_to(2 * hor_grid * 1.12, i * ver_grid)
            cr.line_to(2 * hor_grid * 1.18, i * ver_grid)
            cr.stroke()
            if i % 5 == 0:
                if i % 10 == 0:
                    font_size = 12.0 * w * 0.004
                    self.set_font(cr, font_size, bold=True)
                else:
                    font_size = 10.0 * w * 0.004
                    self.set_font(cr, font_size)
                _, _, ww, hh, _, _ = cr.text_extents(str(i))
                cr.move_to((2 * hor_grid * 1.05) - ww / 1.8, (h - i * ver_grid) + hh / 2)
                cr.show_text(str(i))

        cr.set_source_rgb(0.4, 0.4, 0.4)
        cr.move_to(2 * hor_grid * 0.92, 0)
        cr.line_to(2 * hor_grid * 0.92, h)
        cr.set_line_width(0.5 * lw)
        cr.stroke()
        cr.move_to(2 * hor_grid * 0.95, 0)
        cr.line_to(2 * hor_grid * 0.95, h)
        cr.set_line_width(0.4 * lw)
        cr.stroke()

        cr.set_source_rgb(0.4, 0.4, 0.4)
        cr.move_to(2 * hor_grid * 1.15, 0)
        cr.line_to(2 * hor_grid * 1.15, h)
        cr.set_line_width(0.4 * lw)
        cr.stroke()
        cr.move_to(2 * hor_grid * 1.18, 0)
        cr.line_to(2 * hor_grid * 1.18, h)
        cr.set_line_width(0.5 * lw)
        cr.stroke()

        chartob.__class__ = RadixChart
        plan = [p % 30.0 for p in chartob.get_planets()]
        plan = sorted([(p, i) for i, p in enumerate(plan)])
        fac = [0.7, 1.2]
        plan = self.inject(plan, fac)
        layout = PangoCairo.create_layout(cr)
        font = Pango.FontDescription("Astro-Nex")
        font.set_size(int(11 * Pango.SCALE * w * 0.007))
        layout.set_font_description(font)
        cr.set_source_rgb(0.2, 0.2, 0.2)
        for i, p in enumerate(plan):
            deg = p.deg - p.corr
            layout.set_text(letters[i])
            ink, logical = layout.get_extents()
            ww = logical.width / Pango.SCALE
            hh = logical.height / Pango.SCALE
            cr.move_to((2 * hor_grid * 0.25 * p.fac) - ww / 2, (h - deg * ver_grid) - hh / 2)
            PangoCairo.layout_path(cr, layout)
            cr.fill()
            cr.new_path()
            cr.move_to(2 * hor_grid * 0.4, h - p.deg * ver_grid)
            cr.line_to(2 * hor_grid * 0.44, h - p.deg * ver_grid)
            cr.stroke()
        nplan = self.nodal_lin_planets(chartob)
        plan = sorted([(p, i) for i, p in enumerate(nplan)])
        fac = [0.9, 1.1]
        plan = self.inject(plan, fac)
        cr.set_source_rgb(0.43, 0.0, 0.78)
        for i, p in enumerate(plan):
            deg = p.deg - p.corr
            layout.set_text(letters[i])
            ink, logical = layout.get_extents()
            ww = logical.width / Pango.SCALE
            hh = logical.height / Pango.SCALE
            cr.move_to((2 * hor_grid * 0.7 * p.fac) - ww / 2, (h - deg * ver_grid) - hh / 2)
            PangoCairo.layout_path(cr, layout)
            cr.fill()
            cr.new_path()
            fac[0], fac[1] = fac[1], fac[0]
            cr.move_to(2 * hor_grid * 0.87, h - p.deg * ver_grid)
            cr.line_to(2 * hor_grid * 0.92, h - p.deg * ver_grid)
            cr.stroke()
        chartob.__class__ = SoulChart
        splan = [p % 30.0 for p in chartob.get_planets()]
        plan = sorted([(p, i) for i, p in enumerate(splan)])
        fac = [0.95, 1.05]
        plan = self.inject(plan, fac)
        cr.set_source_rgb(0.76, 0.0, 1.0)
        for i, p in enumerate(plan):
            deg = p.deg - p.corr
            layout.set_text(letters[i])
            ink, logical = layout.get_extents()
            ww = logical.width / Pango.SCALE
            hh = logical.height / Pango.SCALE
            cr.move_to((2 * hor_grid * 1.45 * p.fac) - ww / 2, (h - deg * ver_grid) - hh / 2)
            PangoCairo.layout_path(cr, layout)
            cr.fill()
            cr.new_path()
            fac[0], fac[1] = fac[1], fac[0]
            cr.move_to(2 * hor_grid * 1.18, h - p.deg * ver_grid)
            cr.line_to(2 * hor_grid * 1.23, h - p.deg * ver_grid)
            cr.stroke()
        cr.restore()

    def draw_soul(self, cr, width, height, chartob=None):
        chartob.__class__ = SoulChart
        chartob.name = 'soul'
        offset = chartob.get_offset()
        cx, cy = width / 2, height / 2
        radius = min(cx, cy)

        cr.save()
        cr.set_line_width(cr.get_line_width() * 0.6)
        self.set_plots(chartob)
        cr.scale(1.4, 1.4)
        self.aspmanager.manage_aspects(cr, radius * R_ASP, chartob.get_planets())
        self.make_plines(cr, radius, chartob, 'INN')
        self.draw_planets(cr, radius, chartob)
        self.make_small_ruler(cr, radius, offset)
        cr.restore()

    def draw_house(self, cr, width, height, chartob=None):
        chartob.__class__ = HouseChart
        chartob.set_iter_sizes()
        offset = chartob.get_offset()
        cx, cy = width / 2, height / 2
        radius = min(cx, cy)

        cr.save()
        cr.set_line_width(cr.get_line_width() * 0.6)
        self.set_plots(chartob)
        cr.scale(1.4, 1.4)
        self.aspmanager.manage_aspects(cr, radius * R_ASP, chartob.get_planets())
        self.make_plines(cr, radius, chartob, 'INN')
        self.draw_planets(cr, radius, chartob)
        self.make_small_ruler(cr, radius, offset)
        cr.restore()

    def make_small_ruler(self, cr, radius, offset):
        rules = [0.015, 0.010, 0.005]
        insets = [radius * i for i in rules]
        radius = radius * 0.48

        default = insets.pop()
        insets = dict(zip((0, 5), insets))
        cr.save()
        cr.set_source_rgb(0, 0, 0)
        cr.set_line_width(0.5 * cr.get_line_width())
        for i in range(360):
            angle = (offset + i) * RAD
            inset = radius - insets.get(i % 10, default)
            self.d_radial_line(cr, radius, inset, angle)

        cr.set_source_rgb(1, 1, 1)
        cr.arc(0, 0, radius * 0.15, 0, 360 * RAD)
        cr.fill_preserve()
        cr.set_source_rgb(0, 0, 0)
        cr.set_line_width(0.5 * cr.get_line_width())
        cr.stroke()
        cr.arc(0, 0, radius / 90, 0, 360 * RAD)
        cr.fill()
        cr.restore()

    def plot_cons_plan(self, cr, h, chartob):
        chartob.__class__ = RadixChart
        dplan = [p % 30.0 for p in chartob.get_planets()]
        plan = sorted([(p, i) for i, p in enumerate(dplan)])
        asc = chartob.chart.houses[0] % 30.0
        diffs = []
        for p in plan:
            d = p[0] - asc
            if d < -15.0:
                d += 30.0
            elif d > 15.0:
                d = 30.0 - d
            diffs.append((d, p[1]))
        diffs = sorted(diffs, key=lambda x: abs(x[0]))
        asc = chartob.chart.houses[0]
        dplan = chartob.get_planets()
        wit = diffs[0][0]
        cons = []
        for i, p in enumerate(diffs):
            deg = dplan[p[1]]
            a = int(round(abs(asc - deg) / 30.0))
            if abs(p[0] - wit) <= 1.0:
                cons.append((a, p[1]))
                wit = p[0]
            else:
                break
            if i >= 2:
                break
        layout = PangoCairo.create_layout(cr)
        font = Pango.FontDescription("Astro-Nex")
        font.set_size(14 * Pango.SCALE)
        layout.set_font_description(font)
        cr.save()
        cr.set_source_rgb(1.0, 0.1, 1.0)
        for i, c in enumerate(cons):
            label = "%s%s" % (alet[c[0]], letters[c[1]])
            layout.set_text(label)
            cr.move_to(22, (h - 110) + 24 * i)
            PangoCairo.show_layout(cr, layout)
        cr.restore()

    def draw_label(self, cr, w, h, chartob):
        chart = chartob.chart
        layout = PangoCairo.create_layout(cr)
        font = Pango.FontDescription(self.opts.font)
        font.set_size(12 * Pango.SCALE)
        layout.set_font_description(font)
        cr.save()
        cr.set_source_rgb(0, 0.7, 0.1)
        name = "%s %s" % (chart.first, chart.last)
        layout.set_text(name)
        cr.move_to(20, h - 25)
        PangoCairo.show_layout(cr, layout)
        cr.restore()

    def nodal_lin_planets(self, chartob, plot="plot1"):
        cusps = chartob.get_cusps_offsets()
        asc = chartob.chart.houses[0]
        cusps = [c % 360 for c in cusps]
        sizes = chartob.get_sizes()
        chartob.__class__ = NodalChart
        plots = self.set_plots(chartob, plot)
        degs = []
        for plot in plots:
            plot.degree %= 360.0
            h = (5 - int(plot.degree / 30)) % 12
            dist = 30.0 - plot.degree % 30.0
            degree = (cusps[h] - dist * sizes[h] / 30.0) % 360
            degree = (180 + asc - degree) % 360
            degs.append(degree % 30)
        return degs

    def marshall(self, plans):
        '''Partition planets too close in groups'''
        def diftuple(t):
            d = t[1][0] - t[0][0]
            if d < 0:
                d += 360
            return d <= 3

        planque = deque(plans)
        boolque = deque([diftuple(t) for t in zip(plans, plans[1:] + [plans[0]])])
        if True in boolque:
            while boolque[0] is not True or boolque[-1] is not False:
                boolque.rotate(-1)
                planque.rotate(-1)

        jail = []
        cell = set()
        for low, btuple in zip(planque, boolque):
            cell.add((low[0], low[1]))
            if btuple is False:
                jail.append(cell)
                cell = set()
        return jail

    def inject(self, plan, facs):
        jail = self.marshall(plan)
        plots = [None] * 11

        class plot_obj(object):
            pass

        for cell in jail:
            num_plans = len(cell)
            fac = facs[:]
            gen_corr = 1.5
            witness = sorted(cell)
            for pos, pl in enumerate(witness):
                po = plot_obj()
                po.deg = pl[0]
                if num_plans < 2:
                    po.fac = 1.0
                else:
                    po.fac = fac[0]
                    fac[0], fac[1] = fac[1], fac[0]
                if num_plans < 3:
                    po.corr = 0.0
                else:
                    faraway = pos - (num_plans // 2)
                    if faraway < 0:
                        diff = dif(pl[0], witness[pos + 1][0])
                    elif faraway > 0:
                        diff = dif(witness[pos - 1][0], pl[0])
                        if diff >= 353.5:
                            diff = -(diff - 353.5)
                    po.corr = -faraway * (gen_corr - diff) / 2.5
                plots[pl[1]] = po
        return plots

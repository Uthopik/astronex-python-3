# -*- coding: utf-8 -*-
from gi.repository import Gtk, Gdk, Pango, PangoCairo

from astronex.drawing.paarwabe import ascent_texts, wunder_texts, polar_texts


def _boss():
    from astronex.boss import boss
    return boss


def _curr():
    return _boss().get_state()


textops = ['text_for_ascent', 'text_for_wunder', 'text_for_polar']


def _make_layout(cr, font_str, size, weight=None, style=None):
    layout = PangoCairo.create_layout(cr)
    font = Pango.FontDescription.from_string(font_str)
    font.set_size(int(size * Pango.SCALE))
    if weight is not None:
        font.set_weight(weight)
    if style is not None:
        font.set_style(style)
    layout.set_font_description(font)
    return layout


class PlanPopup(Gtk.Window):
    def __init__(self, boss, persistent=False):
        # Ventana TOPLEVEL (con barra de titulo -> movible por el usuario), en
        # vez de POPUP borderless pegada al cursor que tapaba la carta y no se
        # podia mover (bug Errores2 #4).
        Gtk.Window.__init__(self, type=Gtk.WindowType.TOPLEVEL)
        self.persistent = persistent
        self.set_title(_("Grados"))
        self.set_resizable(False)
        self.set_skip_taskbar_hint(True)
        try:
            self.set_transient_for(boss.mainwin)
        except Exception:
            pass
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.KEY_PRESS_MASK)
        self.connect('button-press-event', self.on_button_press)
        self.connect('key-press-event', self.on_key_press_event)
        self.area = PetitArea(boss.opts.zodiac)
        self.add(self.area)
        self.set_default_size(115, 195)
        self.set_position(Gtk.WindowPosition.NONE)
        # ESC / g / clic / la X = OCULTAR (no destruir) y reutilizar luego.
        # Destruir esta ventana en GTK3/WSLg provocaba un segfault que mataba
        # toda la app; al no destruirla NUNCA durante la sesion se evita el
        # camino de finalizacion que crasheaba. La instancia se conserva en
        # self.planpopup (layoutsurface) y se vuelve a mostrar con reopen().
        self.connect('delete-event', self.on_delete)
        self.reopen(boss)

    def reopen(self, boss):
        """Mostrar (o re-mostrar) la instancia reutilizada: reposicionar al
        borde derecho de la ventana principal, redibujar y presentar."""
        self.show_all()
        self.set_position(Gtk.WindowPosition.NONE)
        # Aparcar al borde derecho de la ventana principal, FUERA de la carta.
        try:
            wx, wy = boss.mainwin.pos_x, boss.mainwin.pos_y
            ww, wh = boss.mainwin.get_size()
            popup_w = 115
            x = wx + ww - popup_w - 10
            y = wy + 40
            scrw = getattr(boss.mainwin, 'scr_width', x + popup_w)
            if x + popup_w > scrw:
                x = scrw - popup_w - 10
            self.move(x, y)
        except Exception:
            self.set_position(Gtk.WindowPosition.CENTER)
        self.area.queue_draw()
        self.present()

    def on_button_press(self, a, event):
        if self.persistent:
            return False
        self.hide()
        return True

    def on_key_press_event(self, window, event):
        if event.keyval == Gdk.KEY_Escape or event.keyval == Gdk.KEY_g:
            self.hide()
            return True
        return False

    def on_delete(self, widget, event):
        # No destruir: ocultar (return True evita el destroy por defecto)
        self.hide()
        return True


class PetitArea(Gtk.DrawingArea):
    zodlet = ('q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', 'a', 's')
    planlet = ['d', 'f', 'h', 'j', 'k', 'l', 'g', 'z', 'x', 'c', 'v']

    def __init__(self, zodiac):
        self.zod = zodiac.zod
        self.plan = zodiac.plan
        Gtk.DrawingArea.__init__(self)
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.connect("draw", self.dispatch)

    def dispatch(self, da, cr):
        alloc = self.get_allocation()
        w = alloc.width
        h = alloc.height
        cr.rectangle(0, 0, w, h)
        cr.clip()
        cr.set_source_rgb(0.96, 0.96, 0.99)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        self.data_planh(cr)
        return True

    def data_planh(self, cr):
        boss = _boss()
        curr = _curr()
        cr.set_source_rgb(0, 0, 0.4)
        if curr.curr_op == 'draw_transits':
            chart = curr.now
        else:
            chart = curr.curr_chart
        signs = chart.calc_plan_with_retrogression(boss.state.epheflag)

        layout = _make_layout(cr, "Astro-Nex", 11)
        for i in range(11):
            cr.move_to(10, 10 + i * 16)
            colp = self.plan[i].col
            cr.set_source_rgb(*colp)
            layout.set_text("%s" % self.planlet[i], -1)
            PangoCairo.show_layout(cr, layout)
            cr.new_path()

        cr.set_source_rgb(0, 0, 0.4)
        layout = _make_layout(cr, boss.opts.font, 9)
        for i in range(11):
            cr.move_to(30, 10 + i * 16)
            layout.set_text(signs[i]['deg'], -1)
            PangoCairo.show_layout(cr, layout)
            cr.new_path()

        layout = _make_layout(cr, "Astro-Nex", 11)
        for i in range(11):
            cr.move_to(86, 10 + i * 16)
            col = self.zod[signs[i]['col'] % 4].col
            cr.set_source_rgb(*col)
            layout.set_text("%s" % (self.zodlet[signs[i]['name']]), -1)
            PangoCairo.show_layout(cr, layout)
            cr.new_path()

        cr.set_source_rgb(0, 0, 0.4)
        layout = _make_layout(cr, boss.opts.font, 9)
        for i in range(11):
            if signs[i]['speed'] < 0:
                cr.move_to(72, 10 + i * 16)
                layout.set_text('r', -1)
                PangoCairo.show_layout(cr, layout)
                cr.new_path()


class TextPopup(Gtk.Window):
    def __init__(self, index):
        Gtk.Window.__init__(self, type=Gtk.WindowType.POPUP)
        # Dar un parent para evitar el aviso GTK3 "temporary window without
        # parent" (Errores2 #8). Sigue apareciendo junto al cursor.
        try:
            self.set_transient_for(_boss().mainwin)
        except Exception:
            pass
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.KEY_PRESS_MASK)
        self.connect('button-press-event', self.on_button_press)
        self.connect('key-press-event', self.on_key_press_event)
        # OCULTAR (no destruir) y reutilizar: destruir en GTK3/WSLg crashea.
        # La instancia se conserva en self.textspopup (layoutsurface) y se
        # reutiliza re-apuntandola a otro texto con set_index().
        self.connect('delete-event', self.on_delete)
        self.area = None
        self.set_index(index)
        self.set_default_size(420, 200)
        self.set_position(Gtk.WindowPosition.MOUSE)
        self.show_all()

    def set_index(self, index):
        """(Re)construir el area de texto para el index dado sobre la MISMA
        ventana, sin destruirla. Permite reutilizar la instancia al hacer
        scroll a otro texto."""
        if self.area is not None:
            self.remove(self.area)
            self.area.destroy()
        self.area = TextArea(index)
        self.add(self.area)
        self.area.show_all()
        self.area.queue_draw()

    def reopen(self, index):
        """Re-mostrar la instancia reutilizada apuntando al texto pedido."""
        self.set_index(index)
        self.set_position(Gtk.WindowPosition.MOUSE)
        self.show_all()
        self.present()

    def on_button_press(self, a, event):
        self.hide()
        return True

    def on_key_press_event(self, window, event):
        if event.keyval == Gdk.KEY_Escape:
            self.hide()
            return True
        return False

    def on_delete(self, widget, event):
        # No destruir: ocultar (return True evita el destroy por defecto)
        self.hide()
        return True


class TextArea(Gtk.DrawingArea):
    def __init__(self, index):
        self.index = index
        Gtk.DrawingArea.__init__(self)
        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.connect("draw", self.dispatch, index)

    def dispatch(self, da, cr, index):
        alloc = self.get_allocation()
        w = alloc.width
        h = alloc.height
        cr.rectangle(0, 0, w, h)
        cr.clip()
        cr.set_source_rgb(0.9, 0.96, 0.9)
        cr.rectangle(0, 0, w, h)
        cr.fill_preserve()
        cr.set_source_rgb(0.4, 0.6, 0.4)
        cr.set_line_width(3)
        cr.stroke()
        getattr(self, textops[index - 2])(cr, w)
        return True

    def _draw_text_line(self, cr, layout, text, x, y):
        layout.set_text(text, -1)
        cr.move_to(x, y)
        PangoCairo.show_layout(cr, layout)

    def text_for_ascent(self, cr, width):
        boss = _boss()
        v = width * 0.05
        fem_col = (0, 0.2, 0.6)
        mas_col = (0.7, 0, 0)
        layout = _make_layout(cr, boss.opts.font, 10)
        cr.translate(6, 6)
        cr.set_source_rgb(*mas_col)
        self._draw_text_line(cr, layout, "1  %s" % ascent_texts['a1'], 0, 0)
        self._draw_text_line(cr, layout, "2  %s" % ascent_texts['a2'], 0, v)
        self._draw_text_line(cr, layout, "3  %s" % ascent_texts['a3'], 0, v * 2)
        self._draw_text_line(cr, layout, "%s" % ascent_texts['a3b'], 0, v * 3)
        self._draw_text_line(cr, layout, "4  %s" % ascent_texts['a4'], 0, v * 4)
        self._draw_text_line(cr, layout, "%s" % ascent_texts['a4b'], 0, v * 5)
        cr.set_source_rgb(*fem_col)
        self._draw_text_line(cr, layout, "5/6  %s" % ascent_texts['a5'], 0, v * 6)
        self._draw_text_line(cr, layout, "7/8  %s" % ascent_texts['a7'], 0, v * 7)

    def text_for_polar(self, cr, width):
        boss = _boss()
        r = width / 2
        v = r * 0.05
        pol_col = (0, 0.7, 0)
        fem_col = (0, 0.2, 0.6)
        mas_col = (0.7, 0, 0)

        cr.translate(r, 0)
        r *= 0.9
        cr.set_source_rgb(1.0, 1, 0.8)
        cr.rectangle(-r * 1.05, 10.2 * v * 0.97, 2 * r * 1.05, 6 * v)
        cr.fill()

        layout = _make_layout(cr, boss.opts.font, 10)

        def measure_h(text):
            layout.set_text(text, -1)
            _, logical = layout.get_extents()
            return logical.height / Pango.SCALE

        def measure_w(text):
            layout.set_text(text, -1)
            _, logical = layout.get_extents()
            return logical.width / Pango.SCALE

        text = "6  %s" % polar_texts['P6']
        h = measure_h(text)
        cr.move_to(-r, 1.5 * v - h / 2)
        cr.set_source_rgb(*mas_col)
        PangoCairo.show_layout(cr, layout)

        text = "5 %s" % polar_texts['P5']
        w = measure_w(text)
        h = measure_h(text)
        cr.move_to(r - w, 1.5 * v - h / 2)
        cr.set_source_rgb(*mas_col)
        PangoCairo.show_layout(cr, layout)

        text = "14  %s" % polar_texts['P14']
        w = measure_w(text)
        h = measure_h(text)
        cr.move_to(-w / 2, 3 * v - h / 2)
        cr.set_source_rgb(*pol_col)
        PangoCairo.show_layout(cr, layout)

        text = "9  %s" % polar_texts['P9']
        h = measure_h(text)
        cr.move_to(-r, 4.5 * v - h / 2)
        cr.set_source_rgb(*fem_col)
        PangoCairo.show_layout(cr, layout)

        text = "10  %s" % polar_texts['P10']
        w = measure_w(text)
        h = measure_h(text)
        cr.move_to(r - w, 4.5 * v - h / 2)
        cr.set_source_rgb(*fem_col)
        PangoCairo.show_layout(cr, layout)

        text = "13  %s" % polar_texts['P13']
        w = measure_w(text)
        h = measure_h(text)
        cr.move_to(-w / 2, 6 * v - h / 2)
        cr.set_source_rgb(*pol_col)
        PangoCairo.show_layout(cr, layout)

        text = "4  %s" % polar_texts['P4']
        h = measure_h(text)
        cr.move_to(-r, 7.5 * v - h / 2)
        cr.set_source_rgb(*mas_col)
        PangoCairo.show_layout(cr, layout)

        text = "3  %s" % polar_texts['P3']
        w = measure_w(text)
        h = measure_h(text)
        cr.move_to(r - w, 9 * v - h / 2)
        cr.set_source_rgb(*mas_col)
        PangoCairo.show_layout(cr, layout)

        text = "12  %s" % polar_texts['P12']
        w = measure_w(text)
        h = measure_h(text)
        cr.move_to(-w / 2, 10.5 * v - h / 2)
        cr.set_source_rgb(*pol_col)
        PangoCairo.show_layout(cr, layout)

        text = "7  %s" % polar_texts['P7']
        h = measure_h(text)
        cr.move_to(-r, 12 * v - h / 2)
        cr.set_source_rgb(*fem_col)
        PangoCairo.show_layout(cr, layout)

        text = "8  %s" % polar_texts['P8']
        w = measure_w(text)
        h = measure_h(text)
        cr.move_to(r - w, 12 * v - h / 2)
        cr.set_source_rgb(*fem_col)
        PangoCairo.show_layout(cr, layout)

        text = "11  %s" % polar_texts['P11']
        w = measure_w(text)
        h = measure_h(text)
        cr.move_to(-w / 2, 13.5 * v - h / 2)
        cr.set_source_rgb(*pol_col)
        PangoCairo.show_layout(cr, layout)

        text = "2 %s" % polar_texts['P2']
        h = measure_h(text)
        cr.move_to(-r, 15 * v - h / 2)
        cr.set_source_rgb(*fem_col)
        PangoCairo.show_layout(cr, layout)

        text = "1 %s" % polar_texts['P1']
        w = measure_w(text)
        h = measure_h(text)
        cr.move_to(r - w, 15 * v - h / 2)
        cr.set_source_rgb(*mas_col)
        PangoCairo.show_layout(cr, layout)

    def text_for_wunder(self, cr, width):
        boss = _boss()
        v = width * 0.045
        mar = 12
        w_col = (0.6, 0, 0.6)
        s_col = (0, 0.6, 0.2)
        layout = _make_layout(cr, boss.opts.font, 10,
                              weight=Pango.Weight.NORMAL,
                              style=Pango.Style.NORMAL)

        cr.translate(6, 6)
        cr.set_source_rgb(*w_col)
        self._draw_text_line(cr, layout, "1  %s" % wunder_texts['w1'], 0, 0)
        self._draw_text_line(cr, layout, "2  %s" % wunder_texts['w2'], 0, v)
        self._draw_text_line(cr, layout, "3  %s" % wunder_texts['w3'], 0, v * 2)
        self._draw_text_line(cr, layout, "4  %s" % wunder_texts['w4'], 0, v * 3)
        cr.set_source_rgb(*s_col)

        def right_align(text, y):
            layout.set_text(text, -1)
            _, logical = layout.get_extents()
            w = logical.width / Pango.SCALE
            cr.move_to(width - mar - w, y)
            PangoCairo.show_layout(cr, layout)

        right_align("1  %s" % wunder_texts['s1'], v * 4)
        right_align("2  %s" % wunder_texts['s2'], v * 5)
        right_align("3  %s" % wunder_texts['s3'], v * 6)
        right_align("4  %s" % wunder_texts['s4'], v * 7)
        right_align("5  %s" % wunder_texts['s5'], v * 8)

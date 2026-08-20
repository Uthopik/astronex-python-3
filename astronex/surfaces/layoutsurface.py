# -*- coding: utf-8 -*-
import cairo
import math
from datetime import datetime, timedelta

from gi.repository import Gtk, Gdk, GLib, Pango, PangoCairo

from astronex.drawing.dispatcher import DrawMixin
from astronex.gui.plselector_dlg import PlanSelector
from astronex.gui.popup import PlanPopup, TextPopup, PetitArea
from astronex.gui.cycle_dlg import CycleSelector
from astronex.gui.aux_dlg import AuxWindow
from astronex.gui.bridgewin import BridgePEWindow, BridgeArea
from astronex.extensions.path import path
from astronex.countries import cata_reg
from astronex.utils import parsestrtime
from astronex.surfaces.sdasurface import DrawDiagram, HouseSelector


def _boss():
    from astronex.boss import boss
    return boss


def _curr():
    return _boss().get_state()


def _hex_to_rgb(hex_str):
    s = hex_str.lstrip('#')
    if len(s) >= 12:
        return (int(s[0:4], 16) / 65535.0,
                int(s[4:8], 16) / 65535.0,
                int(s[8:12], 16) / 65535.0)
    return (int(s[0:2], 16) / 255.0,
            int(s[2:4], 16) / 255.0,
            int(s[4:6], 16) / 255.0)


initmenu = (_('Ayuda'), _('Acercar'), _('Solo EA'), _('Ver zonas PE'),
            _('Ver zonas de casa'), _('Ver EA'), _('Activar goodwill'),
            _('Ocultar unilaterales'), _('Ego-clics'), _('Ver todos los aspectos'))
bios = ['bio_nat', 'bio_nod', 'bio_soul', 'bio_dharma']
peops = ['draw_nat', 'draw_nod', 'draw_soul', 'draw_local']
sheetops = ['dat_nat', 'dat_nod', 'dat_house', 'prog_nat', 'prog_nod', 'prog_local', 'prog_soul']
extended = ['prog_nat', 'prog_nod', 'prog_soul', 'prog_local', 'compo_one', 'compo_two']


class DrawMaster(Gtk.Layout):
    fullscreen = False
    panning = False
    zoom_in = False
    panelvisible = False
    diadavisible = False
    hselvisible = False
    pepending = [False, None, None]
    rulinepending = None
    bridge = None
    sec_alltimes = False
    overlay = False

    def __init__(self, boss):
        self.boss = boss
        self.opts = boss.opts
        Gtk.Layout.__init__(self)
        self.menu = Gtk.Menu()
        self.hidden_op = {}
        for buf in initmenu:
            menu_item = Gtk.MenuItem(label=buf)
            self.menu.append(menu_item)
            menu_item.connect("activate", self.on_menuitem_activate)
            if buf in [_('Ayuda'), _('Ver EA')]:
                sep_item = Gtk.SeparatorMenuItem()
                self.menu.append(sep_item)
                sep_item.show()
            if buf not in [_('Ver EA'), _('Ver zonas PE'), _('Ver zonas de casa'),
                           _('Ver todos los aspectos'), _('Ego-clics')]:
                menu_item.show()
            elif buf == _('Ver EA'):
                self.hidden_op['ea'] = menu_item
            elif buf == _('Ver zonas PE'):
                self.hidden_op['pez'] = menu_item
            elif buf == _('Ver zonas de casa'):
                self.hidden_op['hz'] = menu_item
            elif buf == _('Ver todos los aspectos'):
                self.hidden_op['acl'] = menu_item
            elif buf == _('Ego-clics'):
                self.hidden_op['ego'] = menu_item

        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK |
                        Gdk.EventMask.POINTER_MOTION_HINT_MASK)
        self.connect("draw", self.dispatch)
        self.connect("button-press-event", self.on_da_clicked)
        self.connect("button-release-event", self.on_da_clicked)
        self.connect("motion-notify-event", self.on_da_clicked)
        self.connect("scroll-event", self.on_scroll)
        # Tras un cambio de tamano (arranque, cambio a biografia que redimensiona
        # el canvas, zoom...) el primer dibujo es transitorio y la etiqueta de
        # fecha/hora/regente arriba-derecha puede no pintarse. Forzar un redibujo
        # limpio cuando la asignacion cambia garantiza que aparezca sin tener que
        # hacer zoom manualmente.
        self._last_alloc_size = (0, 0)
        self.connect("size-allocate", self._on_size_allocate)
        self._move_info = {'button': -1, 'click_x': 0, 'click_y': 0}
        # Calendario embebido en el canvas (como el Py2 original), esquina
        # superior-izquierda. Antes se hizo como ventana flotante porque salia
        # invisible, pero la causa era el cr.identity_matrix() del dispatch (ya
        # corregido); ahora los hijos del Layout se dibujan en su posicion real.
        self.panel = ChangeDatePanel(self)
        self.put(self.panel, 0, 0)
        self.panel.set_no_show_all(True)
        self.panel.hide()

        self.create_special_area()
        self.create_hselector()
        self.drawer = DrawMixin(boss.opts, self)
        self.plselector = None
        self.cycleselector = None
        self.planpopup = None
        self.textspopup = None
        # Paneles acoplados al canvas (como el calendario): tabla de grados (G)
        # y selector de aspectos (Ctrl+H). Se crean al primer uso. Asi aparecen
        # FUERA de la carta, en una esquina, y el WM no los recoloca.
        self.gradospanel = None
        self.gradosarea = None
        self.plselpanel = None
        self._plsel_notwanted = set()
        self._plsel_buttons = []
        self.bridgepanel = None
        self.bridgearea = None
        self._where_bridge = None
        self.where_diada = 0
        self.where_hsel = 0
        self.auxwins = []

        self.ha = None
        self.va = None
        self.m_x = 0
        self.m_y = 0

    def create_special_area(self):
        frame = Gtk.Frame()
        diada = DrawDiagram(self.boss)
        diada.set_size_request(275, 275)
        frame.add(diada)
        self.put(frame, 0, 0)
        frame.set_no_show_all(True)
        frame.hide()
        self.diada = frame

    def create_hselector(self):
        frame = Gtk.Frame()
        hsel = HouseSelector(self.boss)
        hsel.set_size_request(120, 120)
        frame.add(hsel)
        self.put(frame, 0, 0)
        frame.set_no_show_all(True)
        frame.hide()
        self.hsel = frame

    def on_da_clicked(self, da, event):
        boss = _boss()
        curr = _curr()
        showAP = DrawMixin.get_showAP()
        x, y = event.x, event.y
        info = self._move_info
        if event.type == Gdk.EventType.BUTTON_PRESS and event.button == 3:
            self.menu.popup_at_pointer(event)
            return True
        if event.type == Gdk.EventType._2BUTTON_PRESS and event.button == 1:
            if showAP or curr.curr_chart == curr.now or curr.curr_op in ['draw_transits', 'rad_and_transit']:
                self.panel.nowbut.emit('clicked')
                info['button'] = 100
                if self.cycleselector:
                    cycles = curr.curr_chart.get_cycles()
                    self.cycleselector.adj.set_value(cycles + 1)
            elif curr.curr_op == 'sec_prog':
                self.sec_alltimes = not self.sec_alltimes
            return True
        elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 1:
            if curr.curr_op in bios and curr.opmode == 'simple':
                return False
            if event.button != 1:
                return False
            if info['button'] < 0:
                info['button'] = event.button
                if self.panning:
                    info['click_x'] = event.x
                    info['click_y'] = event.y
            elif info['button'] == 100:
                info['button'] = -1
            if showAP is None:
                return True
            alloc = da.get_allocation()
            w = alloc.width / 2
            h = alloc.height / 2
            if curr.opmode == 'simple' and curr.curr_op in peops:
                pass
            elif curr.opmode == 'double' or curr.curr_op == 'rad_and_transit':
                deg = math.degrees(math.atan2(y - h, (x % w) - (w / 2)))
                for_op = [curr.opleft, curr.opright][x > w]
                if curr.clickmode == 'click':
                    for_ch = ['chart', 'click'][x > w]
                else:
                    for_ch = 'chart'
                if deg == 0.0:
                    deg = 0.0001
                self.drawer.set_AP(deg, for_op, for_ch)
                self.redraw()
                dt = curr.date.dt
                dt = datetime.combine(dt.date(), dt.time())
                self.hsel.get_child().set_house_from_date(dt)
                self.redraw_auxwins()
                info['button'] = -1
            else:
                return False
            return True
        elif event.type == Gdk.EventType.BUTTON_PRESS and event.button == 2:
            if curr.clickmode == 'click' and curr.opmode != 'simple':
                return
            if curr.opmode == 'double':
                boss.mpanel.chooser.swap_ops()
                boss.da.redraw_auxwins(True)
            elif curr.opmode == 'triple':
                alloc = da.get_allocation()
                w, h = alloc.width, alloc.height
                side = ['up', None][y > (h / 2)]
                if not side:
                    side = ['left', 'right'][x > (w / 2)]
                boss.mpanel.chooser.swap_ops(side)
            elif curr.opmode == 'simple':
                if self.zoom_in:
                    self.panning = not self.panning
                elif not showAP:
                    nb = boss.mpanel.chooser.notebook
                    page = nb.get_current_page()
                    sel = nb.get_nth_page(page).get_selection()
                    m, i = sel.get_selected()
                    ix = m.get_path(i)[0]
                    if ix == 0:
                        if self.planpopup is None:
                            self.planpopup = PlanPopup(boss)
                        elif not self.planpopup.get_visible():
                            self.planpopup.reopen(boss)
                    elif page == 3 and ix in [2, 3, 4]:
                        if self.textspopup is None:
                            self.textspopup = TextPopup(ix)
                        elif not self.textspopup.get_visible():
                            self.textspopup.reopen(ix)
                else:
                    self.drawer.set_op_AP(curr.curr_op, event.state)
                    dt = curr.date.dt
                    dt = datetime.combine(dt.date(), dt.time())
                    self.hsel.get_child().set_house_from_date(dt)
                    self.redraw()
                    self.redraw_auxwins()
        elif event.type == Gdk.EventType.BUTTON_RELEASE:
            if self.planpopup and not getattr(self.planpopup, 'persistent', False):
                self.planpopup.hide()
            if curr.curr_op in bios or curr.opmode != 'simple':
                return False
            if info['button'] < 0 or info['button'] == 100:
                return True
            if info['button'] == event.button:
                info['button'] = -1
                if self.panning:
                    pass
                else:
                    self.drawer.ruline = None
                    self.rulinepending = None
                    if showAP:
                        alloc = da.get_allocation()
                        w = alloc.width / 2
                        h = alloc.height / 2
                        deg = math.degrees(math.atan2(y - h, x - w))
                        for_op = curr.curr_op
                        for_ch = 'chart'
                        self.drawer.set_AP(deg, for_op, for_ch)
                        dt = curr.date.dt
                        dt = datetime.combine(dt.date(), dt.time())
                        self.hsel.get_child().set_house_from_date(dt)
                    self.redraw()
                    boss.redraw(both=False)
                    self.redraw_auxwins()
        elif event.type == Gdk.EventType.MOTION_NOTIFY:
            if curr.curr_op in bios or curr.opmode != 'simple':
                return False
            x = event.x
            y = event.y
            if DrawMaster.overlay:
                self.m_x = x
                self.m_y = y
                self.queue_draw()
            if info['button'] < 0 or info['button'] == 100:
                info['button'] = -1
                return False
            alloc = da.get_allocation()
            w = alloc.width / 2
            h = alloc.height / 2
            if self.panning:
                dx = info['click_x'] - x
                dy = info['click_y'] - y
                w = alloc.width
                h = alloc.height
                wrange = w - self.ha.get_page_size()
                hrange = h - self.va.get_page_size()
                cur_h = self.ha.get_value()
                cur_v = self.va.get_value()
                if dx + cur_h < 0:
                    self.ha.set_value(0)
                elif dx + cur_h > wrange:
                    self.ha.set_value(wrange)
                else:
                    self.ha.set_value(cur_h + dx)
                if dy + cur_v < 0:
                    self.va.set_value(0)
                elif dy + cur_v > hrange:
                    self.va.set_value(hrange)
                else:
                    self.va.set_value(cur_v + dy)
            else:
                self.drawer.ruline = (x - w, y - h)
                self.queue_draw()

    def toggle_planpopup(self):
        """Tecla G: alterna la tabla de grados como panel ACOPLADO al canvas
        (esquina superior-derecha, fuera de la carta), igual que el calendario,
        en vez de una ventana flotante que tapaba la carta."""
        if self.gradospanel is not None and self.gradospanel.get_visible():
            self.gradospanel.hide()
            return
        if self.gradospanel is None:
            frame = Gtk.Frame()
            self.gradosarea = PetitArea(_boss().opts.zodiac)
            self.gradosarea.set_size_request(115, 195)
            frame.add(self.gradosarea)
            self.put(frame, 0, 0)
            frame.set_no_show_all(True)
            self.gradospanel = frame
        alloc = self.get_allocation()
        x = max(5, alloc.width - 125)
        self.move(self.gradospanel, x, 24)
        self.gradospanel.set_no_show_all(False)
        self.gradospanel.show_all()
        self.gradospanel.set_no_show_all(True)
        self.gradosarea.queue_draw()

    def toggle_overlay(self):
        DrawMaster.overlay = not DrawMaster.overlay
        win = self.get_window()
        if DrawMaster.overlay and win is not None:
            display = self.get_display()
            cursor = Gdk.Cursor.new_for_display(display, Gdk.CursorType.BLANK_CURSOR)
            win.set_cursor(cursor)
        elif win is not None:
            win.set_cursor(None)
        self.queue_draw()

    def on_scroll(self, da, event):
        boss = _boss()
        curr = _curr()
        x, y = event.x, event.y
        alloc = da.get_allocation()
        w, h = alloc.width, alloc.height
        side = None

        if event.direction == Gdk.ScrollDirection.UP:
            delta = -1
        elif event.direction == Gdk.ScrollDirection.DOWN:
            delta = 1
        elif event.direction == Gdk.ScrollDirection.SMOOTH:
            ok, dx, dy = event.get_scroll_deltas()
            if not ok or dy == 0:
                return True
            delta = -1 if dy < 0 else 1
        else:
            return True

        if self.textspopup and self.textspopup.get_visible():
            self.textspopup.hide()
            nb = boss.mpanel.chooser.notebook
            page = nb.get_current_page()
            m, i = nb.get_nth_page(page).get_selection().get_selected()
            ix = m.get_path(i)[0] + delta
            if page == 3 and ix in [2, 3, 4]:
                self.textspopup.reopen(ix)

        if curr.opmode == 'simple':
            boss.mpanel.chooser.delta_select(delta)
        elif curr.opmode == 'triple':
            side = ['up', None][y > (h / 2)]
            if not side:
                side = ['left', 'right'][x > (w / 2)]
            curr.set_opdelta(delta, side)
            boss.mpanel.chooser.delta_triple_select(delta, side)
        elif curr.opmode == 'double':
            side = ['left', 'right'][x > (w / 2)]
            curr.set_opdelta(delta, side)
            boss.mpanel.chooser.delta_double_select(delta, side)

        self.redraw()
        return True

    def on_menuitem_activate(self, menuitem):
        boss = _boss()
        label = menuitem.get_label()
        if label == _('Acercar'):
            scrw, scrh = self.get_size_request()
            self.set_size_request(scrw * 2, scrh * 2)
            self.zoom_in = True
            self.panning = True
            menuitem.set_label(_('Alejar'))
            self.queue_resize()
        elif label == _('Alejar'):
            scrw, scrh = self.get_size_request()
            self.set_size_request(scrw // 2, scrh // 2)
            self.zoom_in = False
            self.panning = False
            menuitem.set_label(_('Acercar'))
            self.queue_resize()
        elif label == _('Ayuda'):
            boss.mainwin.show_help()
        elif label == _('Ver zonas PE'):
            self.drawer.pe_zones = True
            self.redraw_auxwins(True)
            menuitem.set_label(_('Ocultar zonas PE'))
        elif label == _('Ocultar zonas PE'):
            self.drawer.pe_zones = False
            self.redraw_auxwins(True)
            menuitem.set_label(_('Ver zonas PE'))
        elif label == _('Ver zonas de casa'):
            self.drawer.hzones = True
            menuitem.set_label(_('Ocultar zonas de casa'))
        elif label == _('Ocultar zonas de casa'):
            self.drawer.hzones = False
            menuitem.set_label(_('Ver zonas de casa'))
        elif label == _('Solo EA'):
            DrawMixin.set_onlyEA(True)
            menuitem.set_label(_('Mostrar todo'))
        elif label == _('Mostrar todo'):
            DrawMixin.set_onlyEA(False)
            menuitem.set_label(_('Solo EA'))
        elif label == _('Activar goodwill'):
            self.drawer.goodwill = True
            menuitem.set_label(_('Desactivar goodwill'))
        elif label == _('Desactivar goodwill'):
            self.drawer.goodwill = False
            menuitem.set_label(_('Activar goodwill'))
        elif label == _('Ocultar unilaterales'):
            self.drawer.uniaspect = False
            menuitem.set_label(_('Mostrar unilaterales'))
        elif label == _('Mostrar unilaterales'):
            self.drawer.uniaspect = True
            menuitem.set_label(_('Ocultar unilaterales'))
        elif label == _('Ver EA'):
            DrawMixin.set_showEA(True)
            menuitem.set_label(_('Ocultar EA'))
        elif label == _('Ocultar EA'):
            DrawMixin.set_showEA(False)
            menuitem.set_label(_('Ver EA'))
        elif label == _('Ver todos los aspectos'):
            self.drawer.allclick = True
            menuitem.set_label(_('Ver solo clics'))
        elif label == _('Ver solo clics'):
            self.drawer.allclick = False
            menuitem.set_label(_('Ver todos los aspectos'))
        elif label == _('Ego-clics'):
            self.drawer.egoclick = True
            menuitem.set_label(_('Clics sin ego'))
        elif label == _('Clics sin ego'):
            self.drawer.egoclick = False
            menuitem.set_label(_('Ego-clics'))

        self.redraw()

    def toggle_menulist(self, men, dothing):
        if dothing == 'add':
            self.hidden_op[men].show()
        elif dothing == 'remove':
            self.hidden_op[men].hide()

    def popup_menu(self):
        self.menu.popup_at_pointer(None)

    def redraw(self):
        self.queue_draw()
        if self.gradospanel is not None and self.gradospanel.get_visible():
            self.gradosarea.queue_draw()
        if self.bridgepanel is not None and self.bridgepanel.get_visible():
            self.bridgearea.queue_draw()

    def _on_size_allocate(self, widget, alloc):
        size = (alloc.width, alloc.height)
        if size != self._last_alloc_size:
            self._last_alloc_size = size
            # Redibujo limpio en idle (tras asentarse la asignacion) para que
            # las etiquetas superiores se pinten en el dibujo transitorio inicial.
            GLib.idle_add(self._idle_redraw)

    def _idle_redraw(self):
        self.queue_draw()
        return False  # one-shot

    def redraw_auxwins(self, onlybridge=False):
        if self.bridgepanel is not None and self.bridgepanel.get_visible():
            self.bridgearea.redraw()
        if onlybridge:
            return
        for aux in self.auxwins:
            aux.sda.redraw()

    def show_panel(self, menuitem=None):
        self.move(self.panel, 0, 0)
        self.panel.set_no_show_all(False)
        self.panel.show_all()
        self.panel.set_no_show_all(True)
        self.panelvisible = True
        self.queue_draw()

    def hide_panel(self, menuitem=None):
        self.panel.hide()
        self.panelvisible = False
        curr = _curr()
        if curr.curr_chart == curr.now:
            self.panel.nowbut.emit('clicked')
        self.queue_draw()

    def show_pe(self, menuitem=None):
        curr = _curr()
        boss = _boss()
        if curr.curr_chart == curr.now:
            boss.mpanel.toolbar.get_nth_item(1).set_active(False)
            return
        DrawMixin.set_showAP('now')
        self.redraw()
        self.redraw_auxwins()

    def hide_pe(self, menuitem=None):
        DrawMixin.set_showAP(None)
        self.redraw()
        self.redraw_auxwins()

    def show_diada(self, menuitem=None):
        alloc = self.get_allocation()
        aw = alloc.width if alloc.width > 275 else 720
        where = aw - 275
        self.move(self.diada, where, 0)
        self.diada.set_no_show_all(False)
        self.diada.show_all()
        self.diada.set_no_show_all(True)
        self.diadavisible = True
        self.redraw()

    def hide_diada(self, menuitem=None):
        self.diada.hide()
        self.diadavisible = False
        self.redraw()

    def make_auxwin(self):
        boss = _boss()
        self.auxwins.append(AuxWindow(boss.mainwin))
        sda = self.auxwins[-1].sda
        alloc = sda.get_allocation()
        sda.drawer.hoff = alloc.width * 0.125
        sda.drawer.gridw = sda.drawer.hoff * 6

    BRIDGE_MAX = 450
    BRIDGE_MIN = 260

    def _bridge_geom(self):
        """Lado y posicion del panel del PE Puente: pegado a la esquina inferior
        DERECHA y, en lo posible, SIN pisar el circulo de la carta.

        El cliente pidio que saliera abajo a la derecha "en lugar de encima de la
        carta" (Errores2 #6). Con lado fijo 450 se metia dentro del circulo
        (medido: panel en 1036,543 de 452x452 con la carta en 246,0 de 993x993).
        La carta es un circulo inscrito de radio min(w,h)/2 centrado en el
        lienzo, asi que basta con exigir que la esquina superior-izquierda del
        panel quede fuera de ese circulo; se prueba de mayor a menor y se para en
        BRIDGE_MIN para que el puente siga siendo legible aunque no quepa.
        """
        alloc = self.get_allocation()
        w = alloc.width
        h = alloc.height
        if w <= 1 or h <= 1:
            lado = self.BRIDGE_MAX
            return lado, max(0, w - lado), max(0, h - lado)
        cx, cy = w / 2.0, h / 2.0
        r = min(w, h) / 2.0
        lado = min(self.BRIDGE_MAX, w, h)
        while lado > self.BRIDGE_MIN:
            x0, y0 = w - lado, h - lado
            # esquina del panel mas cercana al centro de la carta
            dx, dy = x0 - cx, y0 - cy
            if dx * dx + dy * dy >= r * r:
                break
            lado -= 10
        lado = max(self.BRIDGE_MIN, min(lado, w, h))
        return lado, max(0, w - lado), max(0, h - lado)

    def make_pebridge(self):
        """PE Puente como panel ACOPLADO al canvas (esquina inferior-DERECHA,
        como en el original), en vez de ventana flotante."""
        lado, bx, by = self._bridge_geom()
        if self.bridgepanel is None:
            frame = Gtk.Frame()
            self.bridgearea = BridgeArea(_boss(), self.drawer.get_AP_DEG)
            self.bridgearea.set_size_request(lado, lado)
            frame.add(self.bridgearea)
            self.put(frame, 0, 0)
            frame.set_no_show_all(True)
            self.bridgepanel = frame
        elif self.bridgearea.get_size_request() != (lado, lado):
            self.bridgearea.set_size_request(lado, lado)
        self._where_bridge = (bx, by)
        self.move(self.bridgepanel, *self._where_bridge)
        self.bridgepanel.set_no_show_all(False)
        self.bridgepanel.show_all()
        self.bridgepanel.set_no_show_all(True)
        # redibujar el canvas para ocultar la etiqueta de nombre principal
        # (la del puente ocupa esa esquina) y pintar el puente.
        self.redraw()

    def hide_pebridge(self):
        if self.bridgepanel is not None:
            self.bridgepanel.hide()
        # redibujar para que reaparezca la etiqueta de nombre de la carta
        self.redraw()

    @staticmethod
    def _aspsel_markup(let, colhex, hidden):
        """Glifo del planeta: a su color cuando es visible; atenuado y tachado
        cuando esta oculto, para que se distinga de un vistazo."""
        if hidden:
            return ("<span font='Astro-Nex 13' foreground='#b3b3b3' "
                    "strikethrough='true'>%s</span>" % let)
        return "<span font='Astro-Nex 13' foreground='%s'>%s</span>" % (colhex, let)

    def _build_plsel_panel(self):
        """Selector de aspectos ('Ocultar' planetas) acoplado al canvas, con
        diseno claro: glifos al COLOR de cada planeta, botones planos y
        redondeados, panel con esquinas redondeadas y sombra; el planeta oculto
        se ve atenuado y tachado. Reutiliza DrawMixin.notwanted."""
        zod = _boss().opts.zodiac
        plet = ['d', 'f', 'h', 'j', 'k', 'l', 'g', 'z', 'x', 'c', 'v']

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.get_style_context().add_class('aspsel-panel')
        title = Gtk.Label(label=_("Ocultar"))
        title.get_style_context().add_class('aspsel-title')
        outer.pack_start(title, False, False, 0)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.pack_start(box, False, False, 0)

        # Estilo CLARO (encaja con el canvas blanco aunque el tema GTK sea
        # oscuro): botones planos, sin caja, redondeados; panel con sombra.
        css = Gtk.CssProvider()
        css.load_from_data(b"""
            .aspsel-panel {
                background-color: #f7f8fd;
                border: 1px solid #c9cde3;
                border-radius: 8px;
                padding: 4px 5px;
                box-shadow: 0 1px 5px rgba(40, 44, 70, 0.25);
            }
            .aspsel-title {
                color: #5a5f7a;
                font-size: 10px;
                font-weight: bold;
                padding-bottom: 3px;
            }
            .aspsel-panel button {
                background-image: none;
                background-color: transparent;
                border: 1px solid transparent;
                border-radius: 6px;
                box-shadow: none;
                text-shadow: none;
                min-height: 0;
                padding: 2px 12px;
                margin: 1px 0;
            }
            .aspsel-panel button:hover { background-color: #e7eaf8; border-color: #cfd4ec; }
            .aspsel-panel button:checked { background-color: #ecedf4; border-color: #dadcec; }
        """)
        Gtk.StyleContext.add_provider_for_screen(
            Gdk.Screen.get_default(), css,
            Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        self._plsel_notwanted = set()
        self._plsel_buttons = []

        def on_tog(but):
            hidden = but.get_active()
            if hidden:
                self._plsel_notwanted.add(but._idx)
            else:
                self._plsel_notwanted.discard(but._idx)
            but._lbl.set_markup(self._aspsel_markup(but._let, but._colhex, hidden))
            DrawMixin.notwanted = list(self._plsel_notwanted)
            self.redraw()
            self.redraw_auxwins()

        for i, let in enumerate(plet):
            colhex = self._col_hex(zod.plan[i].col)
            b = Gtk.ToggleButton()
            b.set_relief(Gtk.ReliefStyle.NONE)
            lbl = Gtk.Label()
            lbl.set_markup(self._aspsel_markup(let, colhex, False))
            b.add(lbl)
            b._idx = i
            b._let = let
            b._colhex = colhex
            b._lbl = lbl
            b.connect("toggled", on_tog)
            box.pack_start(b, False, False, 0)
            self._plsel_buttons.append(b)
        return outer

    def make_plsel(self):
        """Ctrl+H: selector de aspectos como panel ACOPLADO al canvas (esquina
        superior-izquierda, fuera de la carta), igual que el calendario."""
        if self.plselpanel is None:
            self.plselpanel = self._build_plsel_panel()
            self.put(self.plselpanel, 0, 0)
            self.plselpanel.set_no_show_all(True)
        self.move(self.plselpanel, 5, 5)
        self.plselpanel.set_no_show_all(False)
        self.plselpanel.show_all()
        self.plselpanel.set_no_show_all(True)

    def hide_plsel(self):
        if self.plselpanel is not None:
            self.plselpanel.hide()
        DrawMixin.notwanted = []
        self._plsel_notwanted = set()
        for b in self._plsel_buttons:
            b.set_active(False)
        self.redraw()
        self.redraw_auxwins()

    def make_cycleswin(self):
        if not self.cycleselector:
            self.cycleselector = CycleSelector(self.boss.mainwin)
        else:
            # Reutilizar la instancia oculta (no se destruye nunca durante la
            # sesion: evita el segfault de GTK3). Re-sincroniza el spin y la
            # vuelve a mostrar.
            self.cycleselector.refresh_spin()
            self.cycleselector.show_all()
            self.cycleselector.present()
        wx, wy = self.boss.mainwin.pos_x, self.boss.mainwin.pos_y
        ww, wh = self.boss.mainwin.get_size()
        alloc = self.cycleselector.get_allocation()
        w, h = alloc.width, alloc.height
        self.cycleselector.move(wx + ww - w - 10, wh + wy - h - 24)

    def dispatch(self, da, cr):
        curr = _curr()
        boss = _boss()
        # Matriz original del 'draw' (origen = esquina del canvas). Se restaura
        # antes de pintar los hijos (hsel, diada) para que propagate_draw los
        # ubique en coordenadas del canvas y no en el origen de la ventana.
        init_matrix = cr.get_matrix()
        if self.diadavisible:
            alloc = self.get_allocation()
            diada_alloc = self.diada.get_allocation()
            dw = diada_alloc.width if diada_alloc.width > 0 else 275
            where = alloc.width - dw
            if self.where_diada != where:
                self.move(self.diada, where, 0)
                self.where_diada = where

        op = curr.curr_op
        if self.fullscreen:
            DrawMixin.extended_canvas = False
        elif op in extended and curr.opmode == 'simple':
            if not DrawMixin.extended_canvas:
                DrawMixin.extended_canvas = True
                pad = 160
                if op in ['compo_one', 'compo_two']:
                    if boss.mainwin.scr_width <= 1024:
                        pad = 720 * 0.4
                    else:
                        pad = 720 * 0.55
                self.set_size_request(720, int(720 + pad))
        else:
            if DrawMixin.extended_canvas:
                DrawMixin.extended_canvas = False
                self.set_size_request(720, 720)

        alloc = self.get_allocation()
        if op in bios and not self.hselvisible and curr.opmode == 'simple':
            hsel_size = self.hsel.get_size_request()
            hh = hsel_size[1] if hsel_size[1] > 0 else 120
            where = alloc.height - hh
            self.hsel.set_no_show_all(False)
            self.hsel.show_all()
            self.hsel.set_no_show_all(True)
            self.move(self.hsel, 0, where)
            self.hselvisible = True
        elif self.hselvisible and curr.opmode != 'simple' or op not in bios:
            self.hsel.hide()
            self.hselvisible = False

        if self.hselvisible:
            hsel_alloc = self.hsel.get_allocation()
            hh = hsel_alloc.height if hsel_alloc.height > 0 else 120
            where = alloc.height - hh
            if self.where_hsel != where:
                self.move(self.hsel, 0, where)
                self.where_hsel = where

        # Mantener el PE Puente acoplado en la esquina inferior-DERECHA aunque
        # cambie el tamano del lienzo (zoom / modos extendidos).
        if self.bridgepanel is not None and self.bridgepanel.get_visible():
            # Recalcular lado y posicion con el tamano actual del lienzo, para
            # que siga sin pisar el circulo de la carta (ver _bridge_geom).
            lado, bx, by = self._bridge_geom()
            bpos = (bx, by)
            if self.bridgearea is not None and \
                    self.bridgearea.get_size_request() != (lado, lado):
                self.bridgearea.set_size_request(lado, lado)
            if self._where_bridge != bpos:
                self.move(self.bridgepanel, *bpos)
                self._where_bridge = bpos

        w = alloc.width
        h = alloc.height
        cr.rectangle(0, 0, w, h)
        cr.clip()
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.rectangle(0, 0, w, h)
        cr.fill()
        cr.set_line_join(cairo.LINE_JOIN_ROUND)
        cr.set_line_width(float(self.opts.base))

        if self.diadavisible:
            cr.translate(0, h * 0.15)
            w *= 0.85
            h *= 0.85
        self.drawer.dispatch_pres(cr, w, h)
        if self.diadavisible:
            w /= 0.85
            h /= 0.85

        cr.identity_matrix()
        # Etiqueta de fecha/hora/signo Y nombre(s): se actualizan como WIDGETS
        # overlay (fijos, no se duplican al scrollear) en vez de dibujarse con
        # cairo. draw_label solo conserva el caso diada (anclado al panel).
        self._update_datelabel()
        self._update_namelabel()
        if self.rulinepending:
            self.d_ruldegree(cr, w, h)
        self.draw_label(cr, w, h)
        if self.check_local_label():
            self.d_loclbl(cr, w, h)

        if DrawMaster.overlay:
            ovcol = list(_hex_to_rgb('#' + self.opts.overlay)) + [0.5]
            cr.set_source_rgba(*ovcol)
            radial = cairo.RadialGradient(self.m_x, self.m_y, 45, self.m_x, self.m_y, 50)
            radial.add_color_stop_rgba(0.0, 0, 0, 1, 0)
            radial.add_color_stop_rgba(0.9, 1, 0, 0, 1)
            cr.mask(radial)

        cr.set_matrix(init_matrix)
        cr.reset_clip()
        for child in self.get_children():
            if child.get_visible():
                self.propagate_draw(child, cr)
        return True

    def check_local_label(self):
        curr = _curr()
        if curr.opmode == 'simple' and curr.curr_op == 'draw_local':
            return True
        labelyes = curr.opleft == 'draw_local' or curr.opright == 'draw_local'
        if curr.opmode == 'double' and labelyes:
            return True
        if curr.opmode == 'triple' and labelyes or curr.opup == 'draw_local':
            return True
        return False

    def _layout_with_font(self, cr, font_str, size):
        layout = PangoCairo.create_layout(cr)
        font = Pango.FontDescription.from_string(font_str)
        font.set_size(int(size * Pango.SCALE))
        layout.set_font_description(font)
        return layout

    def d_ruldegree(self, cr, w, h):
        if self.diadavisible:
            return
        boss = _boss()
        sign, deg = divmod(self.rulinepending, 30)
        mint = int((deg - int(deg)) * 60)
        sign = int(sign)
        deg = int(deg)
        let = self.drawer.zodlet[sign]
        col = boss.opts.zodiac.zod[sign].col
        signs = "%s° %s´" % (deg, mint)
        cr.set_source_rgb(0, 0, 0.6)
        layout = self._layout_with_font(cr, self.opts.font, 9)
        layout.set_text(signs, -1)
        _, logical = layout.get_extents()
        xpos = logical.width / Pango.SCALE
        cr.move_to(w - xpos - 20, 20)
        PangoCairo.show_layout(cr, layout)

        layout = self._layout_with_font(cr, "Astro-Nex", 9)
        cr.set_source_rgb(*col)
        layout.set_text(let, -1)
        _, logical = layout.get_extents()
        xpos = logical.width / Pango.SCALE
        cr.move_to(w - xpos - 5, 20)
        PangoCairo.show_layout(cr, layout)

    @staticmethod
    def _col_hex(col):
        return '#%02x%02x%02x' % (int(col[0] * 255), int(col[1] * 255), int(col[2] * 255))

    def _update_datelabel(self):
        """Actualiza la etiqueta-widget de la esquina (fecha/hora/signo/regente).

        Reproduce el contenido que antes dibujaban draw_pelabel/d_now_date con
        cairo, pero en un Gtk.Label overlay (fijo, sin duplicarse al scrollear).
        """
        from gi.repository import GLib
        lbl = getattr(self, 'datelabel', None)
        if lbl is None:
            return
        boss = _boss()
        curr = _curr()
        if self.diadavisible:
            lbl.hide()
            return

        esc = GLib.markup_escape_text

        if self.pepending[0]:
            # Punto de Edad (biografias): grado° min´ + fecha + glifo(s) de signo
            d = curr.date.ld.__str__().split(' ')[0].split('-')
            d.reverse()
            d = "/".join(d)
            signs = ['', '']
            glyphs = []
            for i in [1, 2]:
                pe = self.pepending[i]
                if not pe:
                    break
                sign, deg = divmod(pe, 30)
                mint = int((deg - int(deg)) * 60)
                sign = int(sign)
                deg = int(deg)
                signs[i - 1] = "%s° %s´" % (deg, mint)
                glyphs.append((self.drawer.zodlet[sign], boss.opts.zodiac.zod[sign].col))
            if signs[1]:
                signs[0], signs[1] = signs[1], signs[0]
            text = (signs[1] + " " + d + " " + signs[0]).strip()
            markup = "<span foreground='#000099' size='9500'>%s</span>" % esc(text)
            for let, col in glyphs:
                markup += " <span foreground='%s' font='Astro-Nex 11'>%s</span>" % (
                    self._col_hex(col), esc(let))
            lbl.set_markup(markup)
            lbl.show()
            self.pepending = [False, None, None]
        elif curr.curr_chart == curr.now or curr.curr_op in ['draw_transits', 'solar_rev']:
            # Carta del momento / transitos: fecha + hora + planeta regente del ano
            strdate = curr.charts['now'].date
            dt, t = parsestrtime(strdate)
            text = dt + " " + t.split(" ")[0]
            regent = curr.year_regent()
            pl = boss.opts.zodiac.plan[regent]
            markup = ("<span foreground='#000099' size='9500'>%s</span> "
                      "<span foreground='%s' font='Astro-Nex 11'>%s</span>") % (
                esc(text), self._col_hex(pl.col), esc(pl.let))
            lbl.set_markup(markup)
            lbl.show()
        else:
            lbl.hide()

    def _update_namelabel(self):
        """Nombre(s) de la(s) carta(s) como widget(s) overlay (abajo), en vez de
        cairo, para que no se dupliquen al scrollear (scroll-blit GTK3) ni
        dependan del tamano del lienzo. En modo diada se ocultan y los pinta
        draw_label (cairo), anclados al panel de comparacion."""
        from gi.repository import GLib
        lbl = getattr(self, 'namelabel', None)
        lblL = getattr(self, 'namelabel_left', None)
        if lbl is None:
            return
        curr = _curr()
        # Ocultar el nombre cuando hay un panel acoplado que ya muestra el suyo
        # en la misma esquina inferior-derecha (PE Puente), para que no queden
        # dos textos superpuestos.
        bridge_open = (self.bridgepanel is not None
                       and self.bridgepanel.get_visible())
        if curr.curr_op in sheetops or self.diadavisible or bridge_open:
            lbl.hide()
            if lblL is not None:
                lblL.hide()
            return
        esc = GLib.markup_escape_text
        cols = [(0, 0, 0.4), (0.8, 0, 0.1)]
        ix = [0, 1][curr.clickmode == 'click']
        charts = (curr.curr_chart, curr.curr_click)
        # nombre principal -> abajo-derecha (curr_chart en simple, curr_click en clic)
        name0 = ("%s %s" % (charts[ix].first, charts[ix].last)).strip()
        lbl.set_markup("<span foreground='%s' size='9500'>%s</span>" % (
            self._col_hex(cols[ix]), esc(name0)))
        lbl.show()
        if ix and lblL is not None:
            # en clickmode 'click' el segundo nombre (curr_chart) va abajo-izquierda
            name1 = ("%s %s" % (charts[0].first, charts[0].last)).strip()
            lblL.set_markup("<span foreground='%s' size='9500'>%s</span>" % (
                self._col_hex(cols[0]), esc(name1)))
            lblL.show()
        elif lblL is not None:
            lblL.hide()

    def draw_pelabel(self, cr, w, h):
        if self.diadavisible:
            return
        boss = _boss()
        curr = _curr()
        date = curr.date.ld
        date = date.__str__().split(' ')[0].split('-')
        date.reverse()
        date = "/".join(date)

        signs = ['', '']
        collet = [0, 0]
        col = None
        let = None
        for i in [1, 2]:
            pe = self.pepending[i]
            if not pe:
                break
            sign, deg = divmod(pe, 30)
            mint = int((deg - int(deg)) * 60)
            sign = int(sign)
            deg = int(deg)
            let = self.drawer.zodlet[sign]
            col = boss.opts.zodiac.zod[sign].col
            collet[i - 1] = (col, let, i % 2)
            signs[i - 1] = "%s° %s´" % (deg, mint)
        if signs[1]:
            signs[0], signs[1] = signs[1], signs[0]

        cr.set_source_rgb(0, 0, 0.6)
        layout = self._layout_with_font(cr, self.opts.font, 9)
        layout.set_text(signs[1] + " " + date + " " + signs[0], -1)
        _, logical = layout.get_extents()
        xpos = logical.width / Pango.SCALE
        cr.move_to(w - xpos - 20, 5)
        PangoCairo.show_layout(cr, layout)

        layout = self._layout_with_font(cr, "Astro-Nex", 9)
        if collet[1]:
            off = xpos + 22
            for col, let, f in collet:
                cr.set_source_rgb(*col)
                layout.set_text(let, -1)
                _, logical = layout.get_extents()
                xpos = logical.width / Pango.SCALE
                cr.move_to(w - xpos - 5 - f * off, 5)
                PangoCairo.show_layout(cr, layout)
        elif col is not None:
            cr.set_source_rgb(*col)
            layout.set_text(let, -1)
            _, logical = layout.get_extents()
            xpos = logical.width / Pango.SCALE
            cr.move_to(w - xpos - 5, 5)
            PangoCairo.show_layout(cr, layout)

    def d_now_date(self, cr, w, h):
        if self.diadavisible:
            return
        boss = _boss()
        curr = _curr()
        strdate = curr.charts['now'].date
        date, t = parsestrtime(strdate)
        date = date + " " + t.split(" ")[0]
        cr.set_source_rgb(0, 0, 0.6)
        layout = self._layout_with_font(cr, self.opts.font, 9)
        layout.set_text(date, -1)
        _, logical = layout.get_extents()
        xpos = logical.width / Pango.SCALE
        cr.move_to(w - xpos - 18, 5)
        PangoCairo.show_layout(cr, layout)

        layout = self._layout_with_font(cr, "Astro-Nex", 9)
        regent = curr.year_regent()
        pl = boss.opts.zodiac.plan[regent]
        cr.set_source_rgb(*pl.col)
        layout.set_text(pl.let, -1)
        _, logical = layout.get_extents()
        xpos = logical.width / Pango.SCALE
        cr.move_to(w - xpos - 5, 5)
        PangoCairo.show_layout(cr, layout)

    def d_loclbl(self, cr, w, h):
        boss = _boss()
        curr = _curr()
        cr.set_source_rgb(0, 0.5, 0.3)
        layout = self._layout_with_font(cr, self.opts.font, 8)
        region = curr.curr_chart.region
        if boss.opts.lang == 'ca' and curr.curr_chart.country == 'España':
            region = cata_reg[region]
        layout.set_text(curr.curr_chart.city + ' (' + region + '-' + t(curr.curr_chart.country)[0] + ')', -1)
        _, logical = layout.get_extents()
        xpos = logical.width / Pango.SCALE
        cr.move_to(w / 2 - xpos / 2, h - 15)
        PangoCairo.show_layout(cr, layout)

    def draw_label(self, cr, w, h):
        # Los nombres se pintan como widgets Gtk.Label en el overlay
        # (_update_namelabel) para que no se dupliquen con el scroll-blit de GTK3
        # ni dependan de la allocation del lienzo. UNICA excepcion: el modo diada
        # (comparacion de pareja), donde se conserva el dibujo cairo original
        # porque los nombres van anclados al panel diada (incluido el rotado).
        curr = _curr()
        if curr.curr_op in sheetops or not self.diadavisible:
            return
        layout = self._layout_with_font(cr, self.opts.font, 9)
        h -= 20 if self.fullscreen else 15

        cols = [(0, 0, 0.4), (0.8, 0, 0.1)]
        ix = [0, 1][curr.clickmode == 'click']
        charts = (curr.curr_chart, curr.curr_click)
        for i in range(ix + 1):
            name = "%s %s" % (charts[i].first, charts[i].last)
            layout.set_text(name, -1)
            _, logical = layout.get_extents()
            xpos = logical.width / Pango.SCALE
            if ix and not i:
                pos = 0 + 5
            else:
                pos = w - xpos - 5
            cr.set_source_rgb(*cols[i])
            cr.move_to(pos, h)
            PangoCairo.show_layout(cr, layout)
        if curr.clickmode == 'click':
            alloc = self.get_allocation()
            diada_alloc = self.diada.get_allocation()
            where = alloc.width - diada_alloc.width
            name = "%s %s" % (charts[0].first, charts[0].last)
            layout.set_text(name, -1)
            _, logical = layout.get_extents()
            xpos = logical.width / Pango.SCALE
            cr.move_to(where - 20, 5 + xpos)
            cr.rotate(-90 * math.pi / 180)
            cr.set_source_rgb(*cols[0])
            PangoCairo.show_layout(cr, layout)


class ChangeDatePanel(Gtk.Box):
    changes = ['minutes', 'hours', 'days']

    def __init__(self, parent):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL)
        boss = _boss()
        curr = _curr()

        frame = Gtk.Frame()
        self.time = curr.date.ld.time()
        self.internal_signal = True
        self.needsredrawing = True
        self.calendar = Gtk.Calendar()
        self.calendar.set_display_options(
            Gtk.CalendarDisplayOptions.SHOW_HEADING |
            Gtk.CalendarDisplayOptions.SHOW_DAY_NAMES)
        self.calendar.connect('day-selected', self.on_calendar_day_selected, parent)
        self.mth_hid = self.calendar.connect('month-changed', self.on_calendar_day_selected, parent)
        frame.add(self.calendar)
        self.pack_start(frame, False, False, 0)

        self.set_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect("button-press-event", lambda s, ev: True)

        butbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)

        adj = Gtk.Adjustment(value=1, lower=1, upper=10,
                             step_increment=1, page_increment=5, page_size=0)
        self.spin = Gtk.SpinButton()
        self.spin.set_adjustment(adj)
        self.spin.set_wrap(True)
        self.spin.set_alignment(1.0)
        self.spin.set_size_request(40, -1)
        self.spin.set_tooltip_text(_('Cantidad de pasos por clic'))
        butbox.pack_start(self.spin, False, False, 0)

        button = Gtk.Button()
        button.set_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
        arrow = Gtk.Arrow(arrow_type=Gtk.ArrowType.LEFT, shadow_type=Gtk.ShadowType.NONE)
        button.add(arrow)
        button.dir = '<'
        button.connect("button-press-event", self.on_panel_clicked, parent)
        button.connect("button-release-event", self.on_panel_clicked, parent)
        button.set_tooltip_text(_('Retroceder en el tiempo'))
        butbox.pack_start(button, False, False, 0)

        self.combo = Gtk.ComboBoxText()
        self.combo.append_text(_("minutos"))
        self.combo.append_text(_("horas"))
        self.combo.append_text(_("dias"))
        self.combo.set_active(2)
        self.combo.set_size_request(70, -1)
        self.combo.set_tooltip_text(_('Unidad de tiempo'))
        butbox.pack_start(self.combo, False, False, 0)

        button = Gtk.Button()
        button.set_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
        arrow = Gtk.Arrow(arrow_type=Gtk.ArrowType.RIGHT, shadow_type=Gtk.ShadowType.NONE)
        button.add(arrow)
        button.dir = '>'
        button.connect("button-press-event", self.on_panel_clicked, parent)
        button.connect("button-release-event", self.on_panel_clicked, parent)
        button.set_tooltip_text(_('Avanzar en el tiempo'))
        butbox.pack_start(button, False, False, 0)

        but = Gtk.Button()
        img = Gtk.Image()
        appath = boss.app.appath
        imgfile = path.joinpath(appath, "astronex/resources/refresh-18.png")
        img.set_from_file(str(imgfile))
        but.set_image(img)
        butbox.pack_start(but, False, False, 0)
        but.connect('clicked', self.on_now_clicked)
        but.set_tooltip_text(_('Volver al momento actual'))
        self.nowbut = but
        self.pack_start(butbox, False, False, 0)

    def on_calendar_day_selected(self, cal, parent):
        boss = _boss()
        curr = _curr()
        y, m, d = cal.get_date()
        t = self.time
        try:
            date = datetime.combine(datetime(y, m + 1, d), t)
        except ValueError:
            try:
                date = datetime.combine(datetime(y, m + 1, d - 1), t)
            except ValueError:
                date = datetime.combine(datetime(y, m + 1, d - 3), t)
        curr.date.setdt(date)
        curr.refresh_nowchart()
        boss.mpanel.act_now(curr.now)
        if parent.cycleselector:
            cycles = curr.curr_chart.get_cycles(date)
            parent.cycleselector.adj.set_value(cycles + 1)
        if self.internal_signal:
            boss.da.hsel.get_child().set_house_from_date(date)
        if self.needsredrawing:
            parent.redraw()
            parent.redraw_auxwins()
        else:
            self.needsredrawing = True
        self.internal_signal = True

    def on_panel_clicked(self, but, event, parent):
        delta = self.spin.get_value_as_int()
        if getattr(but, 'dir', '>') == '<':
            delta = -delta
        change = self.changes[self.combo.get_active()]
        if event.type == Gdk.EventType.BUTTON_PRESS:
            self.timeout_sid = GLib.timeout_add(80, self.start_spining, delta, change)
        elif event.type == Gdk.EventType.BUTTON_RELEASE:
            GLib.source_remove(self.timeout_sid)

    def start_spining(self, delta, change):
        dt = self.set_delta((delta, change))
        self.set_date(dt, True)
        return True

    def on_now_clicked(self, but):
        self.set_date(datetime.now(), True)

    def update_cycles(self, delta):
        y, m, d = self.calendar.get_date()
        y = y + 72 * delta
        self.set_date(datetime(y, m + 1, d))

    def set_date(self, date, timechanged=False):
        curr = _curr()
        if timechanged:
            self.time = date.time()
            self.internal_signal = True
        else:
            self.time = curr.date.ld.time()
            self.internal_signal = False
        self.set_cal(date)

    def set_cal(self, date):
        self.calendar.handler_block(self.mth_hid)
        self.calendar.select_month(date.month - 1, date.year)
        self.calendar.handler_unblock(self.mth_hid)
        self.calendar.select_day(date.day)
        self.calendar.clear_marks()
        self.calendar.mark_day(date.day)

    def set_date_only(self, date):
        self.time = date.time()
        self.internal_signal = True
        self.set_cal(date)
        self.needsredrawing = False

    def set_delta(self, delta):
        curr = _curr()
        amount = delta[0]
        what = delta[1]
        dt = datetime.combine(curr.date.ld.date(), curr.date.ld.time())
        if what == 'minutes':
            dt = dt + timedelta(minutes=amount)
        elif what == 'hours':
            dt = dt + timedelta(hours=amount)
        elif what == 'days':
            dt = dt + timedelta(days=amount)
        return dt

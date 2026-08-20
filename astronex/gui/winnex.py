# -*- coding: utf-8 -*-
import os
import shlex
import subprocess

from gi.repository import Gtk, Gdk, GdkPixbuf, GLib

from astronex.extensions.path import path
from astronex.surfaces.layoutsurface import DrawMaster
from astronex.surfaces.pngsurface import DrawPng
from astronex.surfaces.pdfsurface import DrawPdf
from astronex.gui.mainnb import MainPanel
from astronex.gui.config_dlg import ConfigDlg
from astronex.gui.customloc_dlg import CustomLocDlg
from astronex.gui.chartbrowser import ChartBrowserWindow
from astronex.gui.plagram_dlg import PlagramWindow
from astronex.gui.entry_dlg import EntryDlg
from astronex.gui.localsel import LocSelector
from astronex.gui.aux_dlg import AuxWindow
from astronex.gui.shell_dlg import ShellDialog
from astronex.gui.quickhelp import HelpWindow
from astronex.gui.inieditor import IniEditor


class WinNex(Gtk.Window):

    def __init__(self, manager):
        Gtk.Window.__init__(self)
        self.boss = manager
        appath = self.boss.app.appath
        appath = path.joinpath(appath, "astronex")
        self.entry = None
        self.locsel = None
        self.locselflag = False
        self.browser = None
        self.plagram = None
        self.help_win = None
        self.config = None
        self.customloc_dlg = None
        self.inieditor = None
        self.about = None
        self.set_title("Astro-Nex")
        self.connect('destroy', self.cb_exit)
        self.connect('key-press-event', self.on_key_press_event)
        self.connect('configure-event', self.on_configure_event)

        accel_group = Gtk.AccelGroup()
        CTRL = Gdk.ModifierType.CONTROL_MASK
        SHIFT = Gdk.ModifierType.SHIFT_MASK
        ALT = Gdk.ModifierType.MOD1_MASK
        LOCKED = Gtk.AccelFlags.LOCKED

        accel_group.connect(ord('j'), CTRL | SHIFT, LOCKED, self.swap_to_ten)
        accel_group.connect(ord('u'), CTRL | SHIFT, LOCKED, self.swap_to_twelve)
        accel_group.connect(ord('e'), CTRL | SHIFT, LOCKED, self.entry_calc)
        accel_group.connect(ord('n'), CTRL, LOCKED, self.locselector)
        accel_group.connect(ord('l'), CTRL, LOCKED, self.customloc_cb)
        accel_group.connect(ord('b'), CTRL, LOCKED, self.launch_chartbrowser)
        accel_group.connect(ord('w'), CTRL, LOCKED, self.launch_aux)
        accel_group.connect(ord('e'), ALT, LOCKED, self.launch_plagram)
        accel_group.connect(ord('r'), CTRL, LOCKED, self.launch_pebridge)
        accel_group.connect(ord('k'), CTRL, LOCKED, self.launch_shell)
        accel_group.connect(ord('i'), CTRL, LOCKED, self.launch_editor)
        accel_group.connect(ord('o'), CTRL, LOCKED, self.toggle_overlay)
        accel_group.connect(Gdk.KEY_g, 0, LOCKED, self.toggle_grados)
        accel_group.connect(Gdk.KEY_F2, 0, LOCKED, self.fake_modify_chart)
        accel_group.connect(Gdk.KEY_F3, 0, LOCKED, self.fake_click_clock)
        accel_group.connect(ord('c'), CTRL, LOCKED, self.launch_calendar)
        accel_group.connect(Gdk.KEY_F4, 0, LOCKED, self.launch_calendar)
        accel_group.connect(Gdk.KEY_F5, 0, LOCKED, self.set_now)
        accel_group.connect(ord('a'), CTRL, LOCKED, self.show_pe)
        accel_group.connect(Gdk.KEY_F6, 0, LOCKED, self.show_pe)
        accel_group.connect(ord('h'), CTRL, LOCKED, self.launch_selector)
        accel_group.connect(ord('y'), CTRL, LOCKED, self.launch_cycles)
        accel_group.connect(ord('d'), CTRL, LOCKED, self.show_diada)
        accel_group.connect(ord('x'), CTRL, LOCKED, self.swap_slot)
        accel_group.connect(ord('z'), CTRL, LOCKED, self.swap_storage)
        accel_group.connect(ord('u'), CTRL, LOCKED, self.load_couple)
        accel_group.connect(ord('1'), ALT, LOCKED, self.load_one_fav)
        accel_group.connect(Gdk.KEY_plus, 0, LOCKED, self.house_change)
        accel_group.connect(Gdk.KEY_minus, 0, LOCKED, self.house_change)
        accel_group.connect(Gdk.KEY_Left, SHIFT, LOCKED, self.view_change)
        accel_group.connect(Gdk.KEY_Right, SHIFT, LOCKED, self.view_change)
        accel_group.connect(Gdk.KEY_Page_Up, CTRL, LOCKED, self.fake_scroll_up)
        accel_group.connect(Gdk.KEY_Page_Down, CTRL, LOCKED, self.fake_scroll_down)
        for i in range(0, 10):
            ksym = getattr(Gdk, "KEY_KP_%s" % i)
            accel_group.connect(ksym, 0, LOCKED, self.page_select)
            accel_group.connect(ksym, CTRL, LOCKED, self.op_select)
        for name in ('Add', 'Subtract'):
            ksym = getattr(Gdk, "KEY_KP_" + name)
            accel_group.connect(ksym, 0, LOCKED, self.scroll_pool)
        accel_group.connect(Gdk.KEY_Menu, 0, LOCKED, self.popup_menu)
        self.add_accel_group(accel_group)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=3)
        self.add(hbox)

        # toolbar
        self.tb = Gtk.Toolbar()
        self.tb.set_size_request(300, -1)
        self.tb.set_style(Gtk.ToolbarStyle.ICONS)

        ti = Gtk.ToolButton()
        ti.connect('clicked', self.cb_exit)
        img = Gtk.Image()
        imgfile = path.joinpath(appath, "resources/gtk-quit-32.png")
        img.set_from_file(str(imgfile))
        ti.set_icon_widget(img)
        ti.add_accelerator('clicked', accel_group, ord('q'), CTRL, LOCKED)
        ti.set_tooltip_text(_("Salir"))
        self.tb.insert(ti, 0)

        tfull = Gtk.ToolButton()
        img = Gtk.Image()
        imgfile = os.path.join(appath, "resources/fullscreen-32.png")
        img.set_from_file(imgfile)
        tfull.set_icon_widget(img)
        tfull.connect('clicked', self.on_fullscreen_clicked)
        tfull.toggled = True
        tfull.set_tooltip_text(_("Pantalla completa"))
        self.tb.insert(tfull, -1)
        self.add_mnemonic(Gdk.KEY_F11, tfull)

        timg = Gtk.ToolButton()
        img = Gtk.Image()
        imgfile = os.path.join(appath, "resources/gnome-image-32.png")
        img.set_from_file(imgfile)
        timg.set_icon_widget(img)
        timg.connect('clicked', self.on_png_clicked)
        timg.add_accelerator('clicked', accel_group, ord('g'), CTRL, LOCKED)
        timg.set_tooltip_text(_("Exportar a imagen"))
        self.tb.insert(timg, -1)

        tpdf = Gtk.ToolButton()
        img = Gtk.Image()
        imgfile = os.path.join(appath, "resources/x-pdf-32.png")
        img.set_from_file(imgfile)
        tpdf.set_icon_widget(img)
        tpdf.connect('clicked', self.on_pdf_clicked)
        tpdf.add_accelerator('clicked', accel_group, ord('p'), CTRL, LOCKED)
        tpdf.set_tooltip_text(_("Exportar a PDF/Imprimir"))
        self.tb.insert(tpdf, -1)

        tentry = Gtk.ToolButton()
        img = Gtk.Image()
        imgfile = os.path.join(appath, "resources/gtk-compose-32.png")
        img.set_from_file(imgfile)
        tentry.set_icon_widget(img)
        tentry.connect('clicked', self.on_entry_clicked)
        tentry.add_accelerator('clicked', accel_group, ord('e'), CTRL, LOCKED)
        tentry.set_tooltip_text(_("TEntradas"))
        self.tentry = tentry
        self.tb.insert(tentry, -1)

        thelp = Gtk.ToolButton()
        img = Gtk.Image()
        imgfile = os.path.join(appath, "resources/gtk-properties-32.png")
        img.set_from_file(imgfile)
        thelp.set_icon_widget(img)
        thelp.connect('clicked', self.on_props_clicked)
        thelp.add_accelerator('clicked', accel_group, ord('s'), CTRL, LOCKED)
        thelp.set_tooltip_text(_("TConfiguracion"))
        self.tb.insert(thelp, -1)

        tabout = Gtk.ToolButton()
        img = Gtk.Image()
        imgfile = os.path.join(appath, "resources/stock_about.png")
        img.set_from_file(imgfile)
        tabout.set_icon_widget(img)
        tabout.connect('clicked', self.on_about_clicked, appath)
        tabout.set_tooltip_text(_("Acerca de Astro-Nex"))
        self.tb.insert(tabout, -1)

        self.mpanel = MainPanel(self.boss)

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(self.tb, False, False, 0)
        vbox.pack_start(self.mpanel, True, True, 0)

        hbox.pack_start(vbox, False, False, 0)
        self.da = DrawMaster(self.boss)
        # Tamaño del MONITOR PRIMARIO (no toda la mesa multi-monitor)
        display = Gdk.Display.get_default()
        monitor = None
        if hasattr(display, 'get_primary_monitor'):
            monitor = display.get_primary_monitor()
        if monitor is None and hasattr(display, 'get_monitor'):
            monitor = display.get_monitor(0)
        if monitor is not None:
            geom = monitor.get_geometry()
            workarea = monitor.get_workarea() if hasattr(monitor, 'get_workarea') else geom
            scr_width = workarea.width
            scr_height = workarea.height
        else:
            screen = Gdk.Screen.get_default()
            scr_width = screen.get_width()
            scr_height = screen.get_height()
        if scr_width >= 1280:
            self.da.set_size_request(660, 660)
        else:
            self.da.set_size_request(500, 500)

        scrolled = Gtk.ScrolledWindow()
        scrolled.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        # Como en PyGTK2 (add_with_viewport): el DrawMaster (Gtk.Layout) va dentro
        # de un Viewport. Asi su set_size_request controla el tamano asignado y el
        # zoom (Acercar/Alejar -> set_size_request*2) genera scrollbars. Sin el
        # Viewport, al ser Gtk.Layout scrollable directo, set_size_request se ignora
        # para el area de scroll y el zoom no hace nada.
        viewport = Gtk.Viewport()
        viewport.set_shadow_type(Gtk.ShadowType.NONE)
        viewport.add(self.da)
        scrolled.add(viewport)
        scrolled.set_shadow_type(Gtk.ShadowType.NONE)
        # La etiqueta de fecha/hora/signo va como WIDGET en un overlay fijo en
        # la esquina superior-derecha, NO dibujada en el canvas con cairo. Asi
        # se mantiene fija y NO se duplica al hacer scroll (el dibujo cairo en
        # el canvas se duplicaba por el "blit" de scroll de GTK3).
        overlay = Gtk.Overlay()
        overlay.add(scrolled)
        self.datelabel = Gtk.Label()
        self.datelabel.set_halign(Gtk.Align.END)
        self.datelabel.set_valign(Gtk.Align.START)
        self.datelabel.set_margin_top(3)
        self.datelabel.set_margin_end(14)
        self.datelabel.set_no_show_all(True)
        overlay.add_overlay(self.datelabel)
        overlay.set_overlay_pass_through(self.datelabel, True)
        # El/los nombre(s) de la carta tambien van como WIDGET en el overlay, fijos
        # abajo (dcha = carta principal/clic; izq = segunda carta en modo clic). Asi
        # no se duplican con el scroll-blit ni dependen del tamano del lienzo.
        self.namelabel = Gtk.Label()
        self.namelabel.set_halign(Gtk.Align.END)
        self.namelabel.set_valign(Gtk.Align.END)
        self.namelabel.set_margin_bottom(6)
        self.namelabel.set_margin_end(8)
        self.namelabel.set_no_show_all(True)
        overlay.add_overlay(self.namelabel)
        overlay.set_overlay_pass_through(self.namelabel, True)
        self.namelabel_left = Gtk.Label()
        self.namelabel_left.set_halign(Gtk.Align.START)
        self.namelabel_left.set_valign(Gtk.Align.END)
        self.namelabel_left.set_margin_bottom(6)
        self.namelabel_left.set_margin_start(8)
        self.namelabel_left.set_no_show_all(True)
        overlay.add_overlay(self.namelabel_left)
        overlay.set_overlay_pass_through(self.namelabel_left, True)
        hbox.pack_start(overlay, True, True, 0)
        self.da.ha = scrolled.get_hadjustment()
        self.da.va = scrolled.get_vadjustment()
        self.da.datelabel = self.datelabel
        self.da.namelabel = self.namelabel
        self.da.namelabel_left = self.namelabel_left

        imgfile = path.joinpath(appath, "resources/iconex-22.png")
        self.set_icon_from_file(str(imgfile))
        # Ventana al 90% del area de trabajo (deja espacio para barra de tareas)
        win_w = int(scr_width * 0.95)
        win_h = int(scr_height * 0.92)
        self.set_default_size(win_w, win_h)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.scr_width = scr_width
        self.show_all()
        wpos = self.get_position()
        self.pos_x = wpos[0]
        self.pos_y = wpos[1]

    def on_configure_event(self, widget, event):
        self.pos_x = event.x
        self.pos_y = event.y

    def on_key_press_event(self, window, event):
        if event.keyval == Gdk.KEY_F11 or (event.keyval == Gdk.KEY_Escape and self.da.__class__.fullscreen):
            self.tb.get_nth_item(1).emit('clicked')
        elif event.keyval == Gdk.KEY_F1:
            self.show_help()
        return False

    def activate_entry(self):
        self.tentry.emit('clicked')

    def cb_exit(self, e):
        Gtk.main_quit()

    def on_pdf_clicked(self, but):
        DrawPdf.clicked(self.boss)

    def on_png_clicked(self, but):
        DrawPng.clicked(self.boss)

    def on_props_clicked(self, but):
        # El dialogo de configuracion se crea una vez y se REUTILIZA (ESC/X lo
        # ocultan, no lo destruyen): asi se evita el segfault de GTK3 al
        # destruirlo. Mismo patron que show_help/help_win.
        if self.config is not None:
            self.config.show_all()
            self.config.present()
            return
        self.config = ConfigDlg(self)

    def on_entry_clicked(self, but):
        if not self.entry:
            self.entry = EntryDlg(self)
        else:
            # El dialogo se oculta (no se destruye) al cerrarlo; reutilizar.
            self.entry.show_all()
            self.entry.present()

    def entry_calc(self, a, b, c, d):
        if not self.entry:
            self.entry = EntryDlg(self)
        else:
            # Reutilizar la instancia oculta.
            self.entry.show_all()
            self.entry.present()
        self.entry.modify_entries(self.boss.state.calc)

    def locselector(self, a, b, c, d):
        self.locselflag = True
        if not self.locsel:
            self.locsel = LocSelector(self)
        else:
            # La instancia se conserva oculta (ya no se destruye al cerrar);
            # la reutilizamos volviendo a mostrarla en vez de recrearla.
            self.locsel.show_all()
            self.locsel.present()

    def on_fullscreen_clicked(self, full):
        if full.toggled:
            full.toggled = False
            self.mpanel.hide()
            self.tb.hide()
            self.boss.set_fullscreen_state(True)
            self.fullscreen()
        else:
            full.toggled = True
            self.tb.show()
            self.mpanel.show()
            self.boss.set_fullscreen_state(False)
            self.unfullscreen()

    def on_kon_clicked(self, but):
        self.boss.ipshell()

    def on_about_clicked(self, but, appath):
        # El dialogo Acerca-de se crea una vez y se REUTILIZA (ESC/Cerrar lo
        # ocultan, no lo destruyen): destruir esta toplevel en GTK3/WSLg
        # provoca un segfault. Mismo patron que show_help/help_win.
        if self.about is not None:
            self.about.show_all()
            self.about.present()
            return
        about = Gtk.AboutDialog()
        about.connect("response", self.on_about_response)
        about.connect("close", self.on_about_close)
        about.connect("delete-event", self.on_about_close)
        about.connect("activate-link", self._on_about_link)
        about.set_program_name("Astro-Nex")
        about.set_version(self.boss.app.version)
        about.set_comments(_("Programa de calculo y dibujo de cartas astrologicas segun el metodo API"))
        copying = path.joinpath(appath, "resources/COPYING")
        with open(copying, encoding='utf-8') as f:
            about.set_license(f.read())
        about.set_copyright("Copyright © 2006")
        about.set_website("https://www.astro-nex.net")
        # Mostrar la pagina de Astro-Nex como texto del enlace, no el generico
        # "Website" (peticion del cliente).
        about.set_website_label("www.astro-nex.net")
        about.set_authors(["Jose Antonio Rodríguez <jar@eideia.net>"])
        imgfile = path.joinpath(appath, "resources/splash.png")
        logo = GdkPixbuf.Pixbuf.new_from_file(str(imgfile))
        about.set_logo(logo)
        self.about = about
        about.show_all()

    def _on_about_link(self, dialog, uri):
        for viewer in ('xdg-open', 'wslview', 'sensible-browser'):
            try:
                result = subprocess.run([viewer, uri],
                                        stdin=subprocess.DEVNULL,
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL,
                                        timeout=2)
                if result.returncode == 0:
                    return True
            except (OSError, FileNotFoundError, subprocess.TimeoutExpired):
                continue
        self._show_uri_fallback(dialog, uri)
        return True

    def _show_uri_fallback(self, parent, uri):
        msg = Gtk.MessageDialog(transient_for=parent, modal=True,
                                message_type=Gtk.MessageType.INFO,
                                buttons=Gtk.ButtonsType.NONE,
                                text=_("No se encontro un navegador instalado"))
        msg.format_secondary_text(_("Copia este enlace y abrelo manualmente:"))
        entry = Gtk.Entry()
        entry.set_text(uri)
        entry.set_editable(False)
        entry.set_can_focus(True)
        entry.select_region(0, -1)
        entry.set_margin_start(12)
        entry.set_margin_end(12)
        entry.set_margin_top(6)
        entry.set_margin_bottom(6)
        msg.get_content_area().pack_end(entry, False, False, 0)
        copy_btn = msg.add_button(_("Copiar"), Gtk.ResponseType.APPLY)
        msg.add_button(_("Cerrar"), Gtk.ResponseType.CLOSE)
        msg.show_all()

        def on_response(dlg, resp):
            if resp == Gtk.ResponseType.APPLY:
                clipboard = Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD)
                clipboard.set_text(uri, -1)
                copy_btn.set_label(_("Copiado"))
            else:
                dlg.hide()  # no destruir toplevel (segfault GTK3/WSLg); ocultar
        msg.connect('response', on_response)
        # Ocultar en 'response' no basta: con ESC/la X, gtk_main_do_event()
        # destruye la ventana si la emision de 'delete-event' acaba en FALSE.
        # connect_after deja actuar al handler de clase (que emite 'response')
        # y ademas devuelve True, evitando el destroy. Ver entry_dlg.py.
        msg.connect_after('delete-event', lambda w, e: True)

    def on_about_response(self, dialog, response):
        if response < 0:
            # Ocultar (no destruir) y reutilizar: destruir esta toplevel en
            # GTK3/WSLg provoca segfault. La instancia se retiene en self.about.
            dialog.hide()

    def on_about_close(self, widget, event=None):
        widget.hide()
        return True

    def customloc_cb(self, acgroup, actable, keyval, mod):
        # El dialogo se crea una vez y se REUTILIZA (ESC/X/_Cerrar lo ocultan,
        # no lo destruyen): asi se evita el segfault de GTK3/WSLg al destruirlo.
        # Al reabrir se resetea OK insensible para que se comporte como nuevo.
        if self.customloc_dlg is not None:
            self.customloc_dlg.set_response_sensitive(Gtk.ResponseType.OK, False)
            self.customloc_dlg.show_all()
            self.customloc_dlg.present()
            return
        self.customloc_dlg = CustomLocDlg(self.boss, self)

    def launch_chartbrowser(self, acgroup, actable, keyval, mod):
        if self.browser is None:
            self.browser = ChartBrowserWindow(self)
        else:
            # Tras un hide() (ESC/X), show_all() vuelve a mostrar la ventana y
            # todos sus hijos antes de traerla al frente. La ventana NUNCA se
            # destruye, por lo que se reutiliza la misma instancia (evita el
            # segfault de destruir/recrear en GTK3/WSLg).
            self.browser.show_all()
            self.browser.deiconify()
            self.browser.present()

    def launch_chartbrowser_from_mpanel(self):
        if self.browser is None:
            self.browser = ChartBrowserWindow(self)
        else:
            self.browser.show_all()
            self.browser.deiconify()
            self.browser.present()

    def launch_plagram(self, acgroup, actable, keyval, mod):
        # La ventana se crea una vez y se REUTILIZA: ESC/X la ocultan (no la
        # destruyen, para evitar el segfault de GTK3/WSLg), y aqui se vuelve a
        # mostrar y traer al frente.
        if self.plagram is None:
            self.plagram = PlagramWindow(self)
        else:
            self.plagram.show_all()
            self.plagram.deiconify()
            self.plagram.present()

    def launch_aux(self, acgroup, actable, keyval, mod):
        self.da.auxwins.append(AuxWindow(self))

    def launch_aux_from_browser(self, chart):
        self.da.auxwins.append(AuxWindow(self, chart=chart))

    def launch_pebridge(self, acgroup, actable, keyval, mod):
        item = self.mpanel.toolbar.get_nth_item(6)
        item.set_active(not item.get_active())

    def launch_shell(self, acgroup, actable, keyval, mod):
        ShellDialog(self.boss)

    def launch_editor(self, acgroup, actable, keyval, mod):
        # El editor de cfg.ini se crea una vez y se REUTILIZA (ESC/Cerrar lo
        # ocultan, no lo destruyen): asi se evita el segfault de GTK3 al destruir.
        if self.inieditor is not None:
            self.inieditor.reload_text()
            self.inieditor.show_all()
            self.inieditor.present()
            return
        self.inieditor = IniEditor(self)

    def launch_calendar(self, acgroup, actable, keyval, mod):
        item = self.mpanel.toolbar.get_nth_item(0)
        item.set_active(not item.get_active())

    def show_pe(self, acgroup, actable, keyval, mod):
        item = self.mpanel.toolbar.get_nth_item(1)
        item.set_active(not item.get_active())

    def launch_selector(self, acgroup, actable, keyval, mod):
        item = self.mpanel.toolbar.get_nth_item(3)
        item.set_active(not item.get_active())

    def launch_cycles(self, acgroup, actable, keyval, mod):
        item = self.mpanel.toolbar.get_nth_item(4)
        item.set_active(not item.get_active())

    def show_diada(self, acgroup, actable, keyval, mod):
        item = self.mpanel.toolbar.get_nth_item(5)
        item.set_active(not item.get_active())

    def swap_slot(self, acgroup, actable, keyval, mod):
        self.mpanel.slot_act_inactive()

    def swap_storage(self, acgroup, actable, keyval, mod):
        self.mpanel.swap_storage()

    def load_one_fav(self, acgroup, actable, keyval, mod):
        self.boss.load_one_fav()

    def load_couple(self, acgroup, actable, keyval, mod):
        self.boss.load_couple()

    def show_help(self):
        # La ventana de ayuda se crea una vez y se REUTILIZA (ESC/X la ocultan,
        # no la destruyen): asi se evita el segfault de GTK3 al destruirla.
        if self.help_win is not None:
            self.help_win.show_all()
            self.help_win.deiconify()
            self.help_win.present()
            return
        self.help_win = HelpWindow(self)

    def swap_to_ten(self, acgroup, actable, keyval, mod):
        self.boss.da.drawer.aspmanager.swap_to_ten()
        self.boss.da.redraw()

    def swap_to_twelve(self, acgroup, actable, keyval, mod):
        self.boss.da.drawer.aspmanager.swap_to_twelve()
        self.boss.da.redraw()

    def page_select(self, acgroup, actable, keyval, mod):
        kcodes = {Gdk.KEY_KP_0: 'transit', Gdk.KEY_KP_1: 'charts', Gdk.KEY_KP_2: 'clicks',
                  Gdk.KEY_KP_3: 'bio', Gdk.KEY_KP_4: 'double1', Gdk.KEY_KP_5: 'triple1',
                  Gdk.KEY_KP_6: 'data', Gdk.KEY_KP_7: 'diagram', Gdk.KEY_KP_8: 'double2',
                  Gdk.KEY_KP_9: 'triple2'}
        thisname = kcodes[keyval]
        for but in self.mpanel.chooser.groups_table.get_children():
            name = getattr(but, 'name_id', None) or getattr(but, 'name', None)
            if name == thisname:
                but.set_active(True)
                break

    def op_select(self, acgroup, actable, keyval, mod):
        kcodes = [Gdk.KEY_KP_0, Gdk.KEY_KP_1, Gdk.KEY_KP_2, Gdk.KEY_KP_3, Gdk.KEY_KP_4,
                  Gdk.KEY_KP_5, Gdk.KEY_KP_6, Gdk.KEY_KP_7, Gdk.KEY_KP_8, Gdk.KEY_KP_9]
        n = kcodes.index(keyval)
        nb = self.boss.mpanel.chooser.notebook
        v = nb.get_nth_page(nb.get_current_page())
        v.get_selection().select_path(n % len(v.get_model()))

    def scroll_pool(self, acgroup, actable, keyval, mod):
        if keyval == Gdk.KEY_KP_Add:
            delta = 1
        elif keyval == Gdk.KEY_KP_Subtract:
            delta = -1
        else:
            return
        self.mpanel.scroll_pool(delta)

    def house_change(self, acgroup, actable, keyval, mod):
        if self.da.hselvisible:
            if keyval == Gdk.KEY_plus:
                self.da.hsel.get_child().house_updown(1)
            else:
                self.da.hsel.get_child().house_updown(-1)

    def view_change(self, acgroup, actable, keyval, mod):
        nb = self.boss.mpanel.chooser.notebook
        page = nb.get_current_page()
        if page < 6:
            return
        if keyval == Gdk.KEY_Right:
            val = 2
        elif keyval == Gdk.KEY_Left:
            val = -2
        else:
            return
        page = nb.get_nth_page(page)
        views = page.get_children()
        n = len(views)
        for v in range(n):
            if views[v].props.has_focus:
                views[(v + val) % (n + 1)].grab_focus()
                break

    def popup_menu(self, acgroup, actable, keyval, mod):
        self.da.popup_menu()

    def fake_scroll_up(self, acgroup, actable, keyval, mod):
        event = Gdk.Event.new(Gdk.EventType.SCROLL)
        event.scroll.direction = Gdk.ScrollDirection.UP
        self.da.on_scroll(self.da, event.scroll)

    def fake_scroll_down(self, acgroup, actable, keyval, mod):
        event = Gdk.Event.new(Gdk.EventType.SCROLL)
        event.scroll.direction = Gdk.ScrollDirection.DOWN
        self.da.on_scroll(self.da, event.scroll)

    def set_now(self, acgroup, actable, keyval, mod):
        self.da.panel.nowbut.emit('clicked')

    def fake_click_clock(self, acgroup, actable, keyval, mod):
        slot = self.mpanel.pool[self.mpanel.active_slot]
        if slot.clock.get_realized():
            slot.clock.emit('clicked')
        else:
            GLib.idle_add(slot.clock.emit, 'clicked')

    def fake_modify_chart(self, acgroup, actable, keyval, mod):
        slot = self.mpanel.pool[self.mpanel.active_slot]
        slot.mod.emit('clicked')

    def toggle_overlay(self, acgroup, actable, keyval, mod):
        self.da.toggle_overlay()

    def toggle_grados(self, acgroup, actable, keyval, mod):
        """Tecla G: alterna ventana de grados persistente."""
        self.da.toggle_planpopup()

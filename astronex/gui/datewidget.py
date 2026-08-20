import datetime
import os
import time

from gi.repository import GObject, GLib, Gtk, Gdk, Pango

from astronex.extensions.validation import MaskEntry, ValidationError


def _get_curr():
    """Acceso lazy al estado global (boss puede no estar listo al importar)."""
    from astronex.boss import boss
    return boss.get_state()


def set_background(widget, color):
    c = color.lstrip('#').lower()
    if c in ('ffffff', 'fff'):
        env_theme = os.environ.get('GTK_THEME', '') or ''
        dark = 'dark' in env_theme.lower()
        if not dark:
            settings = Gtk.Settings.get_default()
            prefer_dark = settings and settings.get_property('gtk-application-prefer-dark-theme')
            theme_name = (settings.get_property('gtk-theme-name') if settings else '') or ''
            dark = prefer_dark or 'dark' in theme_name.lower()
        if dark:
            widget.override_background_color(Gtk.StateFlags.NORMAL, None)
            return
    rgba = Gdk.RGBA()
    rgba.parse(color)
    widget.override_background_color(Gtk.StateFlags.NORMAL, rgba)


class _DateEntryPopup(Gtk.Window):
    __gsignals__ = {
        'date-selected': (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, (object,)),
    }

    def __init__(self, dateentry):
        Gtk.Window.__init__(self, type=Gtk.WindowType.POPUP)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.connect('key-press-event', self._on__key_press_event)
        self.connect('button-press-event', self._on__button_press_event)
        # 'delete-event' -> ocultar (popdown), NUNCA destruir. Salvaguarda con
        # la misma idea aprobada en HelpWindow: destruir esta ventana en GTK3/
        # WSLg dispara un segfault que mata la app. Este popup ya se oculta y
        # se reutiliza (self._popup), aqui solo se evita el destroy por defecto.
        self.connect('delete-event', self._on__delete_event)
        self._dateentry = dateentry

        frame = Gtk.Frame()
        frame.set_shadow_type(Gtk.ShadowType.ETCHED_IN)
        self.add(frame)
        frame.show()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.set_border_width(6)
        frame.add(vbox)
        vbox.show()
        self._vbox = vbox

        self.calendar = Gtk.Calendar()
        self.calendar.connect('day-selected-double-click',
                              self._on_calendar__day_selected_double_click)
        vbox.pack_start(self.calendar, False, False, 0)
        self.calendar.show()

        buttonbox = Gtk.ButtonBox(orientation=Gtk.Orientation.HORIZONTAL)
        buttonbox.set_border_width(6)
        buttonbox.set_layout(Gtk.ButtonBoxStyle.SPREAD)
        vbox.pack_start(buttonbox, False, False, 0)
        buttonbox.show()

        for label, callback in [(_('_Hoy'), self._on_today__clicked),
                                (_('_Cancelar'), self._on_cancel__clicked),
                                (_('_Aceptar'), self._on_select__clicked)]:
            button = Gtk.Button.new_with_mnemonic(label)
            button.connect('clicked', callback)
            buttonbox.pack_start(button, True, True, 0)
            button.show()

        self.set_resizable(False)
        self.set_screen(dateentry.get_screen())

        self.realize()
        __, self.height = self._vbox.get_preferred_height()

    def _on_calendar__day_selected_double_click(self, calendar):
        self.emit('date-selected', self.get_date())

    def _on__delete_event(self, window, event):
        # No destruir: ocultar (return True evita el destroy por defecto).
        self.popdown()
        return True

    def _on__button_press_event(self, window, event):
        hide = False
        alloc = self.get_allocation()
        rect = Gdk.Rectangle()
        rect.x = int(event.x)
        rect.y = int(event.y)
        rect.width = 1
        rect.height = 1
        intersect, __ = Gdk.rectangle_intersect(alloc, rect)
        if not intersect:
            hide = True

        toplevel = event.window.get_toplevel()
        parent = self.calendar.get_parent_window()
        if toplevel != parent:
            hide = True

        if hide:
            self.popdown()

    def _on__key_press_event(self, window, event):
        keyval = event.keyval
        state = event.state & Gtk.accelerator_get_default_mod_mask()
        if (keyval == Gdk.KEY_Escape or
            ((keyval == Gdk.KEY_Up or keyval == Gdk.KEY_KP_Up) and
             state == Gdk.ModifierType.MOD1_MASK)):
            self.popdown()
            return True
        elif keyval == Gdk.KEY_Tab:
            self.popdown()
            return True
        elif keyval in (Gdk.KEY_Return, Gdk.KEY_space,
                        Gdk.KEY_KP_Enter, Gdk.KEY_KP_Space):
            self.emit('date-selected', self.get_date())
            return True

        return False

    def _on_select__clicked(self, button):
        self.emit('date-selected', self.get_date())

    def _on_cancel__clicked(self, button):
        self.popdown()

    def _on_today__clicked(self, button):
        self.set_date(datetime.date.today())

    def _popup_grab_window(self):
        # En GTK3 modernas el grab unificado se hace con Gdk.Seat.
        # Para popups simples basta con make modal y grab_add.
        return True

    def _get_position(self):
        self.realize()
        sample = self._dateentry

        gdk_win = sample.dateentry.get_window()
        if gdk_win is None:
            return 0, 0, 200, self.height
        _, x, y = gdk_win.get_origin()
        width = self.get_preferred_width()[1]
        height = self.height

        screen = sample.get_screen()
        display = screen.get_display()
        monitor = display.get_monitor_at_window(gdk_win)
        monitor_geom = monitor.get_geometry()

        if x < monitor_geom.x:
            x = monitor_geom.x
        elif x + width > monitor_geom.x + monitor_geom.width:
            x = monitor_geom.x + monitor_geom.width - width

        sample_alloc = sample.get_allocation()
        if y + sample_alloc.height + height <= monitor_geom.y + monitor_geom.height:
            y += sample_alloc.height
        elif y - height >= monitor_geom.y:
            y -= height
        elif (monitor_geom.y + monitor_geom.height - (y + sample_alloc.height) >
              y - monitor_geom.y):
            y += sample_alloc.height
            height = monitor_geom.y + monitor_geom.height - y
        else:
            height = y - monitor_geom.y
            y = monitor_geom.y

        return x, y, width, height

    def popup(self, date):
        combo = self._dateentry
        if not combo.get_realized():
            return

        if self.calendar.get_mapped():
            return
        toplevel = combo.get_toplevel()
        if isinstance(toplevel, Gtk.Window):
            # Dar parent para evitar el aviso "temporary window without parent"
            # de GTK3 en esta ventana POPUP (Errores2 #8).
            self.set_transient_for(toplevel)
            group = toplevel.get_group()
            if group is not None:
                group.add_window(self)

        x, y, width, height = self._get_position()
        self.set_size_request(width, height)
        self.move(x, y)
        self.show_all()

        if date:
            self.set_date(date)
        self.grab_focus()

        if not self.calendar.has_focus():
            self.calendar.grab_focus()

        if not self._popup_grab_window():
            self.hide()
            return

        self.grab_add()

    def popdown(self):
        combo = self._dateentry
        if not combo.get_realized():
            return

        self.grab_remove()
        self.hide()

    def get_date(self):
        y, m, d = self.calendar.get_date()
        return datetime.date(y, m + 1, d)

    def set_date(self, date):
        self.calendar.select_month(date.month - 1, date.year)
        self.calendar.select_day(date.day)
        self.calendar.clear_marks()
        self.calendar.mark_day(date.day)


class DateEntry(Gtk.Box):
    __gsignals__ = {
        'changed': (GObject.SignalFlags.RUN_FIRST, GObject.TYPE_NONE, ()),
    }

    def __init__(self, manager, fullpanel=True):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)
        self.boss = manager
        self._popping_down = False
        dt = datetime.datetime.now()
        self.date = dt.date()
        self.time = dt.time()
        self.dateformat = "%d/%m/%Y"
        self.timeformat = "%H:%M:%S"

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.dateentry = MaskEntry()
        self.dateentry.set_mask('00/00/0000')
        self.dateentry.connect('changed', self.on_entry_changed)
        self.dateentry.connect('focus-out-event', self.on_entry_focus_out)
        mask = self.dateentry.get_mask()
        self.dateentry.set_width_chars(len(mask))
        hbox1 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        sg = None
        if fullpanel:
            label = Gtk.Label(label="    " + _("Fecha:") + "    ")
            hbox1.pack_start(label, False, False, 0)
            sg = Gtk.SizeGroup(mode=Gtk.SizeGroupMode.HORIZONTAL)
            sg.add_widget(label)
        hbox1.pack_start(self.dateentry, False, False, 0)

        self._button = Gtk.ToggleButton()
        self._button.connect('scroll-event', self.on_entry_scroll_event)
        self._button.connect('toggled', self.on_button_toggled)
        self._button.set_focus_on_click(False)
        hbox1.pack_start(self._button, False, False, 0)
        self._button.show()

        arrow = Gtk.Arrow(arrow_type=Gtk.ArrowType.DOWN, shadow_type=Gtk.ShadowType.NONE)
        self._button.add(arrow)
        arrow.show()

        self._popup = _DateEntryPopup(self)
        self._popup.connect('date-selected', self._on_popup__date_selected)
        self._popup.connect('hide', self._on_popup__hide)
        self._popup.set_size_request(-1, 24)

        vbox.pack_start(hbox1, False, False, 0)
        if fullpanel:
            label = Gtk.Label(label=_("Hora:"))
            self.timeentry = MaskEntry()
            self.timeentry.set_mask('00:00:00')
            self.timeentry.connect('changed', self.on_entry_changed)
            self.timeentry.connect('focus-out-event', self.on_entry_focus_out)
            mask = self.timeentry.get_mask()
            self.timeentry.set_width_chars(len(mask))
            hbox2 = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
            hbox2.pack_start(label, False, False, 0)
            hbox2.pack_start(self.timeentry, False, False, 0)
            if sg is not None:
                sg.add_widget(label)
            vbox.pack_start(hbox2, False, False, 0)
            self.pack_end(self.create_delta_panel(), False, False, 0)

        self.pack_start(vbox, False, False, 0)

    def create_delta_panel(self):
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        adj = Gtk.Adjustment(value=1, lower=1, upper=15,
                             step_increment=1, page_increment=5, page_size=0)
        spin = Gtk.SpinButton()
        spin.set_adjustment(adj)
        spin.set_wrap(True)
        spin.set_alignment(1.0)
        self.spin = spin
        vbox.pack_start(spin, False, False, 0)

        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        button = Gtk.Button()
        arrow = Gtk.Arrow(arrow_type=Gtk.ArrowType.LEFT, shadow_type=Gtk.ShadowType.NONE)
        button.add(arrow)
        button.dir = '<'
        button.set_size_request(26, -1)
        button.connect('clicked', self.on_panel_arrow_clicked)
        hbox.pack_start(button, False, False, 0)

        button = Gtk.ToggleButton(label=_('minutos'))
        button.set_size_request(60, -1)
        button.connect('toggled', self.on_delta_toggled)
        button.connect('scroll-event', self.on_delta_scroll_event)
        self.hintbut = button
        hbox.pack_start(button, False, False, 0)

        button = Gtk.Button()
        arrow = Gtk.Arrow(arrow_type=Gtk.ArrowType.RIGHT, shadow_type=Gtk.ShadowType.NONE)
        button.add(arrow)
        button.dir = '>'
        button.set_size_request(26, -1)
        button.connect('clicked', self.on_panel_arrow_clicked)
        hbox.pack_start(button, False, False, 0)
        vbox.pack_start(hbox, False, False, 0)
        return vbox

    def do_grab_focus(self):
        self.dateentry.grab_focus()

    def on_entry_changed(self, entry):
        self.calc_and_set(entry)

    def on_entry_focus_out(self, entry, event):
        self.calc_and_set(entry)

    def calc_and_set(self, entry):
        if entry is self.dateentry:
            try:
                self.date = self.get_date()
                set_background(entry, "#ffffff")
            except ValidationError:
                self.date = None
                set_background(entry, "#ff699a")
        elif entry is self.timeentry:
            try:
                self.time = self.get_time()
                set_background(entry, "#ffffff")
            except ValidationError:
                self.time = None
                set_background(entry, "#ff699a")
        curr = _get_curr()
        if self.date is not None and self.time is not None:
            curr.calcdt.setdt(datetime.datetime.combine(self.date, self.time))
        active = self.boss.mpanel.active_slot
        curr.setchart()
        curr.act_pool(active, curr.calc)

    def set_date(self, date):
        if not isinstance(date, datetime.date):
            raise TypeError("date must be a datetime.date instance")
        if date.year < 1900:
            year = date.year
            month = str(date.month).rjust(2, '0')
            day = str(date.day).rjust(2, '0')
            strdate = "%s/%s/%s" % (day, month, year)
            self.dateentry.set_text(strdate)
        else:
            self.dateentry.set_text(date.strftime(self.dateformat))

    def get_date(self):
        text = self.dateentry.get_text()
        if text == "":
            return None
        try:
            dateinfo = time.strptime(text, self.dateformat)
            return datetime.date(*dateinfo[:3])
        except ValueError:
            raise ValidationError('value error: %s' % text)

    def set_time(self, t):
        if not isinstance(t, datetime.time):
            raise TypeError("time must be a datetime.time instance")
        self.timeentry.set_text(t.strftime(self.timeformat))

    def get_time(self):
        text = self.timeentry.get_text()
        if text == "":
            return None
        try:
            dateinfo = time.strptime(text, self.timeformat)
            return datetime.time(*dateinfo[3:6])
        except ValueError:
            raise ValidationError('value error: %s' % text)

    def on_entry_scroll_event(self, entry, event):
        if event.direction == Gdk.ScrollDirection.UP:
            amount = 1
        elif event.direction == Gdk.ScrollDirection.DOWN:
            amount = -1
        elif event.direction == Gdk.ScrollDirection.SMOOTH:
            ok, dx, dy = event.get_scroll_deltas()
            if not ok or dy == 0:
                return
            amount = 1 if dy < 0 else -1
        else:
            return
        try:
            date = self.get_date()
            newdate = date + datetime.timedelta(days=amount)
        except ValidationError:
            newdate = datetime.date.today()
        self.set_date(newdate)

    def on_button_toggled(self, button):
        if self._popping_down:
            return
        try:
            date = self.get_date()
        except ValidationError:
            date = None
        self._popup.popup(date)

    def _on_popup__hide(self, popup):
        self._popping_down = True
        self._button.set_active(False)
        self._popping_down = False

    def _on_popup__date_selected(self, popup, date):
        self.set_date(date)
        popup.popdown()
        self.dateentry.grab_focus()
        self.dateentry.set_position(len(self.dateentry.get_text()))

    def on_panel_arrow_clicked(self, but):
        delta = self.spin.get_value_as_int()
        if getattr(but, 'dir', '>') == '<':
            delta = -delta
        self.change_on_delta(delta)

    def on_delta_toggled(self, but):
        hint = [_('minutos'), _('horas')]
        lbl = hint[int(but.get_active())]
        but.set_label(lbl)

    def on_delta_scroll_event(self, entry, event):
        delta = self.spin.get_value_as_int()
        if event.direction == Gdk.ScrollDirection.UP:
            amount = 1 * delta
        elif event.direction == Gdk.ScrollDirection.DOWN:
            amount = -1 * delta
        elif event.direction == Gdk.ScrollDirection.SMOOTH:
            ok, dx, dy = event.get_scroll_deltas()
            if not ok or dy == 0:
                return
            amount = (1 if dy < 0 else -1) * delta
        else:
            return
        self.change_on_delta(amount)

    def change_on_delta(self, delta):
        changes = {_('minutos'): 'minutes', _('horas'): 'hours'}
        hof = None
        change = changes[self.hintbut.get_label()]
        try:
            t = self.get_time()
        except ValidationError:
            t = None
        if not t:
            t = datetime.time.min
        h = t.hour
        m = t.minute
        s = t.second
        if change == 'minutes':
            mof, m = divmod(m + delta, 60)
            if mof:
                hof, h = divmod(h + mof, 24)
        else:
            hof, h = divmod(h + delta, 24)
        newtime = datetime.time(h, m, s)
        self.set_time(newtime)
        if hof:
            try:
                date = self.get_date()
                newdate = date + datetime.timedelta(days=hof)
            except ValidationError:
                newdate = datetime.date.today()
            self.set_date(newdate)

# -*- coding: utf-8 -*-
import sys
import os
import datetime
import re
import codecs

from gi.repository import Gtk

import astronex.state as state
from astronex.utils import degtodec


def _boss():
    from astronex.boss import boss
    return boss


def _curr():
    return _boss().get_state()


mstar_bugloc = {
    'Jaen': 'Jaén',
    'Almeria': 'Almería',
    'Avila': 'Ávila',
    'Cadiz': 'Cádiz',
    'Caceres': 'Cáceres',
    'Cordoba': 'Córdoba',
    'Leon': 'León',
    'Malaga': 'Málaga',
    'L Palmas de Gran Canaria': 'Las Palmas de Gran Canaria',
}

ccodes = {
    'AFG': 'AF', 'ARM': 'AM', 'ASB': 'AJ', 'BRN': 'BA', 'BD': 'BG',
    'BHU': 'BT', 'BRU': 'BX', 'K': 'CB', 'TJ': 'CH', 'CY': 'CY',
    'GRG': 'GG', 'HKG': 'HK', 'IND': 'IN', 'RI': 'ID', 'IR': 'IR',
    'IRQ': 'IZ', 'IL': 'IS', 'J': 'JA', 'JOR': 'JO', 'KAZ': 'KZ',
    'KOR': 'KN', 'ROK': 'KS', 'KWT': 'KU', 'KIR': 'KG', 'LAO': 'LA',
    'RL': 'LE', 'MAL': 'MY', 'MDV': 'MV', 'MOG': 'MG', 'MYA': 'BM',
    'NEP': 'NP', 'OMN': 'MU', 'PAK': 'PK', 'RP': 'RP', 'Q': 'QA',
    'SA': 'SA', 'SGP': 'SN', 'CL': 'CE', 'SYR': 'SY', 'RC': 'TW',
    'TAJ': 'TI', 'THA': 'TH', 'TR': 'TU', 'TUR': 'TX', 'UAE': 'AE',
    'UZB': 'UZ', 'VN': 'VM', 'YMD': 'YM',
    'DZ': 'AG', 'ANG': 'AO', 'RPH': 'BN', 'RB': 'BC', 'BF': 'UV',
    'BU': 'BY', 'CAM': 'CM', 'KVR': 'CV', 'RCA': 'CT', 'CHA': 'CD',
    'KOM': 'CN', 'RCB': 'CF', 'ZR': 'CG', 'DH': 'DJ', 'ET': 'EG',
    'AQG': 'EK', 'ETH': 'ET', 'GAB': 'GB', 'GAM': 'GA', 'GH': 'GH',
    'GUI': 'GV', 'GBA': 'PU', 'CI': 'IV', 'EAK': 'KE', 'LS': 'LT',
    'LB': 'LI', 'LAR': 'LY', 'RM': 'MA', 'MW': 'MI', 'RMM': 'ML',
    'RIM': 'MR', 'MS': 'MP', 'MY': 'MF', 'MA': 'MO', 'MOZ': 'MZ',
    'NAB': 'WA', 'RN': 'NG', 'WAN': 'NI', 'REU': 'RE', 'RWA': 'RW',
    'SHA': 'SH', 'STP': 'TP', 'SN': 'SG', 'SY': 'SE', 'WAL': 'SL',
    'SP': 'SO', 'ZA': 'SF', 'FS': 'SU', 'SD': 'WZ', 'EAT': 'TZ',
    'TG': 'TO', 'TN': 'TS', 'EAV': 'UG', 'Z': 'ZA', 'ZW': 'ZI',
    'ANT': 'AC', 'RA': 'AR', 'AGU': 'AV', 'BDS': 'BB', 'BPA': 'BD',
    'BS': 'BF', 'BH': 'BH', 'BOL': 'BL', 'BR': 'BR', 'CDN': 'CA',
    'RCH': 'CI', 'CAY': 'CJ', 'CO': 'CO', 'CR': 'CS', 'C': 'CU',
    'WD': 'DO', 'DOM': 'DR', 'EC': 'EC', 'ES': 'ES', 'FGU': 'FG',
    'FGB': 'FK', 'WG': 'GJ', 'GRO': 'GL', 'GKA': 'GP', 'GCA': 'GT',
    'GUY': 'GY', 'RH': 'HA', 'HON': 'HO', 'JA': 'JM', 'MQU': 'MB',
    'MTT': 'MH', 'MEX': 'MX', 'SME': 'NS', 'NIC': 'NU', 'FPY': 'PA',
    'PE': 'PE', 'PA': 'PM', 'SPM': 'SB', 'STL': 'ST', 'TT': 'TD',
    'TCO': 'TK', 'U': 'UY', 'WV': 'VC', 'YV': 'VE', 'VRG': 'VI',
    'AUS': 'AS', 'SOL': 'BP', 'CSP': 'CW', 'FJI': 'FJ', 'FSP': 'FP',
    'KSP': 'KR', 'NKP': 'NC', 'NIU': 'NE', 'NFI': 'NF', 'VAN': 'NH',
    'NSP': 'NR', 'NZ': 'NZ', 'PNG': 'PP', 'PSP': 'PC', 'MSH': 'RM',
    'TSP': 'TL', 'TGA': 'TN', 'TVL': 'TV', 'WFP': 'WF', 'WS': 'WS',
    'AL': 'AL', 'AND': 'AN', 'A': 'AU', 'WRS': 'BO', 'B': 'BE',
    'BHG': 'BK', 'BG': 'BU', 'KRO': 'HR', 'CS': 'EZ', 'DK': 'DA',
    'EST': 'EN', 'FOI': 'FO', 'SF': 'FI', 'F': 'FR', 'D': 'GM',
    'GR': 'GR', 'H': 'HU', 'IS': 'IC', 'IRL': 'EI', 'I': 'IT',
    'LET': 'LG', 'FL': 'LS', 'LIT': 'LH', 'L': 'LU', 'MAK': 'MK',
    'M': 'MT', 'MOL': 'MD', 'MC': 'MN', 'NL': 'NL', 'N': 'NO',
    'PL': 'PL', 'P': 'PO', 'R': 'RO', 'RSM': 'SM', 'YU': 'YI',
    'SLO': 'SI', 'E': 'SP', 'S': 'SW', 'CH': 'SZ', 'UKR': 'UP',
    'GBE': 'UK', 'SCO': 'UK', 'NIR': 'UK', 'SSR': 'RS',
}

usa = {
    'New York': 'Nueva York',
    'South Carolina': 'Carolina del Sur',
    'North Carolina': 'Carolina del Norte',
}

brackets = re.compile(r' \[.*\]?')


class Console(Gtk.Box):
    def __init__(self, font):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.VERTICAL, spacing=2)
        self.set_border_width(2)
        self.scrolledwin = Gtk.ScrolledWindow()
        self.scrolledwin.show()
        self.pack_start(self.scrolledwin, True, True, 1)
        self.text = Gtk.TextView()
        self.text.set_editable(True)
        self.text.set_wrap_mode(Gtk.WrapMode.WORD)
        self.scrolledwin.add(self.text)
        self.buffer = self.text.get_buffer()
        self.end = self.buffer.create_mark('end', self.buffer.get_end_iter(), False)
        font = font.split(" ")[0].rstrip() + " 10"
        self.normal = self.buffer.create_tag('Normal', font=font, foreground='black')
        self.error = self.buffer.create_tag('Error', font=font, foreground='red')
        self.warning = self.buffer.create_tag('Warning', font=font, foreground='blue')
        self.buffer.insert_at_cursor(_("(La importacion puede tardar un poco...)\n"))


def cust_cap(s):
    if s not in ['de', 'del', 'am', 'an', 'der', 'sous', 'im', 'bei', 'sur']:
        return s.capitalize()
    return s


def fix_tname(tn):
    tn = tn.replace(' ', '_')
    if tn == '':
        return tn
    while not tn[0].isalpha():
        tn = tn[1:]
    truetn = tn
    for let in tn:
        if not let.isalnum() and let != '_':
            truetn.replace(let, '')
    return truetn


def parse_aaf(file, tname, con, sim, browser, encoding):
    from sqlite3 import DatabaseError
    curr = _curr()
    doubt = []
    n = 0
    buf = con.buffer
    err = con.error
    warn = con.warning
    try:
        f = codecs.open(file, 'r', encoding)
    except IOError:
        start, end = buf.get_bounds()
        buf.insert_with_tags(end, _("Error abriendo el archivo %s") % file, err)
        return
    pending = False
    buf.set_text('')
    if not sim:
        curr.datab.create_table(tname)
        buf.insert_at_cursor(_("Creada tabla %s\n") % tname)
    ccode = ''
    count = ''
    city = ''
    first = ''
    last = ''
    date = ''
    time = ''
    for line in f:
        start, end = buf.get_bounds()
        if line.startswith('#A93'):
            loc = state.Locality()
            a = line[5:].split(',')
            if a[2] not in ['M', 'F'] and a[3] in ['M', 'F']:
                line = line.replace(',', '', 1)
                a = line[5:].split(',')
            last = a[0].strip()
            first = a[1].strip()
            date = a[3][:-1]
            time = a[4]
            city = a[5].strip()
            ccode = a[6].strip()
            last = last.replace('*', '')
            first = first.replace('*', '')
            city = brackets.sub('', city)
            city = city.split('/')[0]
            city = city.split('-')[0]
            city = city.lower()
            city = ' '.join(cust_cap(s) for s in city.split(' '))
            try:
                ccode = ccodes[ccode]
            except KeyError:
                if ccode.find('-') == -1:
                    ccode = brackets.sub('', ccode)
                    ccode = ccode.strip()
                    if ccode != '':
                        city = ccode + ' ' + city
                    ccode, count = a[7].split('-')
                else:
                    ccode, count = ccode.split('-')
            city = city.strip()
            if city in mstar_bugloc:
                city = mstar_bugloc[city]
            if ccode.startswith('US'):
                loc = curr.datab.fetch_blindly_usacity(ccode[-2:], city, loc)
            else:
                try:
                    ccode = ccodes[ccode]
                except KeyError as arg:
                    buf.insert_with_tags(end,
                                         _("codigo pais no encontrado: %s\n") % arg, err)
                    continue
                loc = curr.datab.fetch_blindly(ccode, city, loc)
            if not isinstance(loc, state.Locality):
                buf.insert_with_tags(end, "%s\n" % loc, err)
                pending = True
                continue
            curr.date.settz(loc.zone)
            d, m, y = date.split('.')
            h, mi, s = time.split(':')
            dt = datetime.datetime(int(y), int(m), int(d), int(h), int(mi), int(s))
            dt = datetime.datetime.combine(dt.date(), dt.time())
            curr.loc = loc
            curr.date.setdt(dt)
            curr.person.first = first
            curr.person.last = last
            curr.setchart()
            if not sim:
                try:
                    curr.datab.store_chart(tname, curr.charts['calc'])
                except DatabaseError:
                    curr.charts['calc'].first += str(n + 1).rjust(3, '0')
                    curr.datab.store_chart(tname, curr.charts['calc'])
            buf.insert_at_cursor(_("Importando %s %s\n") % (first, last))
            con.text.scroll_to_mark(buf.get_insert(), 0.0, True, 0.0, 0.0)
            n += 1
            while Gtk.events_pending():
                Gtk.main_iteration()
        elif pending and line.startswith('#B93'):
            loc = state.Locality()
            b = line[5:].split(',')
            lt1, lt2 = b[1].split(':')
            lg1, lg2 = b[2].split(':')
            lgs = lg1[-3]
            lg = lg1[0:-3] + lg1[-2:] + lg2
            lgs = '-' if lgs == 'E' else ''
            lts = lt1[-3]
            lt = lt1[0:-3] + lt1[-2:] + lt2
            lts = '-' if lts == 'S' else ''
            lgs += lg
            lts += lt
            loc.longitud = lgs
            loc.latitud = lts
            loc.latdec = degtodec(loc.latitud)
            loc.longdec = degtodec(loc.longitud)
            loc.city = city
            loc.country_code = ccode
            count = count.strip()
            if ccode.startswith('US'):
                loc.country = 'USA'
            elif count in ['Escocia']:
                loc.country = 'Gran Bretaña'
            else:
                loc.country = count
            if ccode.startswith('US'):
                if count in ['New York', 'South Carolina', 'Noth Carolina']:
                    count = usa[count]
                st, code = curr.datab.get_usa_state_code(count)
                curr.datab.fetch_blindly_zone_usa(st, code, loc)
            else:
                curr.datab.fetch_blindly_zone(loc)
            pending = False
            doubt.append("%s %s: %s" % (first, last, city))
            curr.date.settz(loc.zone)
            d, m, y = date.split('.')
            h, mi, s = time.split(':')
            dt = datetime.datetime(int(y), int(m), int(d), int(h), int(mi), int(s))
            dt = datetime.datetime.combine(dt.date(), dt.time())
            curr.loc = loc
            curr.date.setdt(dt)
            curr.person.first = first
            curr.person.last = last
            curr.setchart()
            if not sim:
                try:
                    curr.datab.store_chart(tname, curr.charts['calc'])
                except DatabaseError:
                    curr.charts['calc'].first += str(n + 1).rjust(3, '0')
                    curr.datab.store_chart(tname, curr.charts['calc'])
            buf.insert_at_cursor(_("Importando %s %s\n") % (first, last))
            n += 1
            con.text.scroll_to_mark(buf.get_insert(), 0.0, True, 0.0, 0.0)
            while Gtk.events_pending():
                Gtk.main_iteration()

    if not sim:
        browser.tables.emit('changed')
        browser.relist(tname)
    else:
        buf.insert_at_cursor('\nImportacion terminada en modo simulacion\n')
    start, end = buf.get_bounds()
    buf.create_mark('mess', end, True)
    buf.insert_with_tags(end, '\n*******\n', warn)
    buf.insert_at_cursor(_("Cartas importadas: %s; dudosas: %s") % (n, len(doubt)))
    if n > 0:
        buf.insert_at_cursor('(%.2f%%) \n' % (100 * len(doubt) / float(n)))
    buf.insert_at_cursor(_("Las cartas siguientes fueron importadas sin encontrar\n"))
    buf.insert_at_cursor(_("la localidad correspondiente, y la zona horaria sera\n"))
    buf.insert_at_cursor(_("probablemente incorrrecta. Puede editar este panel,\n"))
    buf.insert_at_cursor(_("y copiar su contenido (menu clic derecho)."))
    start, end = buf.get_bounds()
    buf.insert_with_tags(end, '\n*******\n', warn)
    for d in doubt:
        buf.insert_with_tags(end, '%s\n' % d, warn)
    con.text.scroll_to_mark(buf.get_mark('mess'), 0.0, True, 0.0, 0.0)


def dlg_response(ibut, entry, tentry, con, but, enc, browser):
    curr = _curr()
    codes = ['cp1252', 'utf-8']
    file = entry.get_text()
    tname = tentry.get_text()
    tn = fix_tname(tname)
    if entry.get_text() == '' or tn == '':
        return
    tablelist = curr.datab.get_databases()
    simul = but.get_active()
    if not simul:
        if tn in tablelist:
            result = replacedialog(tn)
            if result != Gtk.ResponseType.OK:
                return
    encoding = codes[enc.get_active()]
    parse_aaf(file, tn, con, simul, browser, encoding)


# Singletons de dialogo retenidos a nivel de modulo: NO se destruyen nunca
# durante la sesion (en WSLg/GTK3 destruir un dialogo modal al cerrarlo con
# ESC/X provoca un segfault que mata la app). Se crean una vez y se reutilizan
# ocultandolos (hide) en vez de destruirlos, igual que HelpWindow. Retenerlos
# es necesario: un dialogo solo-oculto sin referencia seria recolectado por el
# GC y su finalizacion dispararia el mismo destroy que segfaultea.
# NO se conecta 'delete-event': gtk_dialog_run() ya lo intercepta por su
# cuenta (devuelve True bloqueando el destroy por defecto) y como aqui ya no
# llamamos a destroy(), cerrar con la X solo hace que run() retorne
# DELETE_EVENT y luego ejecutamos hide().
_browse_dlg = None
_replace_dlg = None


def on_browse_but(but, entry):
    global _browse_dlg
    if _browse_dlg is None:
        _browse_dlg = Gtk.FileChooserDialog(
            title="Abrir archivo...",
            parent=None,
            action=Gtk.FileChooserAction.OPEN,
        )
        _browse_dlg.add_buttons(_("_Cancelar"), Gtk.ResponseType.CANCEL,
                                _("_Abrir"), Gtk.ResponseType.OK)
        _browse_dlg.set_default_response(Gtk.ResponseType.OK)

        filt = Gtk.FileFilter()
        filt.set_name(_("Archivo AAF"))
        filt.add_mime_type("text/plain")
        filt.add_pattern("*.aaf")
        _browse_dlg.add_filter(filt)
    dialog = _browse_dlg
    # Resetear estado en cada apertura para preservar el comportamiento previo
    # (siempre abre en ~ sin seleccion).
    dialog.unselect_all()
    dialog.set_current_folder(os.path.expanduser("~"))

    filename = None
    response = dialog.run()
    if response == Gtk.ResponseType.OK:
        filename = dialog.get_filename()
    dialog.hide()
    if filename:
        entry.set_text(filename)


def replacedialog(tbl):
    global _replace_dlg
    msg = _("La tabla %s existe. Reemplazarla, perdiendo los datos?") % tbl
    if _replace_dlg is None:
        _replace_dlg = Gtk.MessageDialog(transient_for=None, modal=True,
                                         message_type=Gtk.MessageType.WARNING,
                                         buttons=Gtk.ButtonsType.OK_CANCEL,
                                         text=msg)
    dialog = _replace_dlg
    # El nombre de tabla varia en cada uso: actualizar el texto del mensaje.
    dialog.set_property('text', msg)
    result = dialog.run()
    dialog.hide()
    return result


def export_chart(ch):
    return "%s,%s,%s,%s,%s,%s,%s,%s,%s" % (
        ch.last, ch.first, ch.date, ch.city, ch.region, ch.country,
        ch.zone, ch.latitud, ch.longitud)


class ImportPanel(Gtk.Box):
    def __init__(self, parent):
        Gtk.Box.__init__(self, orientation=Gtk.Orientation.HORIZONTAL)
        browser = parent.mpanel.browser
        cons = Console(browser.font)
        self.changes = False

        frame = Gtk.Frame()
        table = Gtk.Table(n_rows=2, n_columns=4, homogeneous=True)
        label = Gtk.Label(label=_('Importar archivo: '))
        entry = Gtk.Entry()
        button = Gtk.Button(label=_('Examinar'))
        button.connect('clicked', on_browse_but, entry)
        table.attach(label, 0, 1, 0, 1)
        table.attach(entry, 1, 2, 0, 1)
        table.attach(button, 2, 3, 0, 1)

        label = Gtk.Label(label=_('Nombre tabla: '))
        tentry = Gtk.Entry()
        tentry.set_text('importemp')
        sim_button = Gtk.CheckButton(label=_('Simular'))
        sim_button.set_active(True)
        table.attach(label, 0, 1, 1, 2)
        table.attach(tentry, 1, 2, 1, 2)
        table.attach(sim_button, 2, 3, 1, 2)

        encoding = Gtk.RadioButton.new_with_label_from_widget(None, 'Win-1252')
        encoding.set_active(True)
        table.attach(encoding, 3, 4, 0, 1)
        encoding2 = Gtk.RadioButton.new_with_label_from_widget(encoding, 'utf-8')
        table.attach(encoding2, 3, 4, 1, 2)

        frame.add(table)
        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        vbox.pack_start(frame, False, False, 0)
        vbox.pack_start(cons, True, True, 0)
        ibutton = Gtk.Button(label=_('Importar'))
        ibutton.connect("clicked", dlg_response, entry, tentry, cons, sim_button, encoding, browser)
        hbox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        hbox.pack_end(ibutton, False, False, 0)
        vbox.pack_start(hbox, False, False, 0)
        frame = Gtk.Frame()
        frame.set_border_width(6)
        frame.add(vbox)
        self.add(frame)

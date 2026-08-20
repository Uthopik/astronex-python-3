# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

UTC = timezone.utc


class NeXDate(object):
    '''Date/time settings.

    Las zonas se manejan con zoneinfo (base IANA del sistema, actualizable via
    tzdata del SO o el paquete tzdata de PyPI). Asi los cambios de horario de
    verano (ej. Mexico 2022) se aplican automaticamente sin ajuste manual.
    Para fechas anteriores a la hora estandar (IANA las etiqueta 'LMT') se usa
    el Tiempo Medio Local calculado por la longitud real del lugar.
    '''

    def __init__(self, current, dt=datetime.now(), tz=UTC):
        self.tz = tz
        if dt.tzinfo is None:
            self.ld = dt.replace(tzinfo=tz)
        else:
            self.ld = dt
        self.dt = self.ld.astimezone(UTC)
        self.current = current

    def _pre_standard(self, dt):
        # IANA marca el periodo previo a la hora estandar con el nombre 'LMT'.
        try:
            return dt.replace(tzinfo=self.tz).tzname() == 'LMT'
        except Exception:
            return dt.year < 1900

    def _apply(self, dt):
        # dt: datetime naive en hora local
        if self._pre_standard(dt):
            # Tiempo Medio Local por longitud: 4 minutos de tiempo por grado.
            # name='LMT' para conservar el formato del campo date al guardar.
            offset = round(self.current.loc.longdec * 4)
            self.ld = dt.replace(tzinfo=timezone(timedelta(minutes=offset), 'LMT'))
        else:
            self.ld = dt.replace(tzinfo=self.tz)
        self.dt = self.ld.astimezone(UTC)

    def settz(self, tz):
        # tz: nombre IANA (str), ej. 'America/Mexico_City'
        self.tz = ZoneInfo(tz)
        dt = datetime.combine(self.ld.date(), self.ld.time())
        self._apply(dt)

    def setdt(self, dt):
        self._apply(dt)

    def set_now(self):
        self.setdt(datetime.now())

    def getnewdt(self, dateset):
        y, m, d, h = dateset
        ho = int(h)
        mi = ((h - ho) * 60)
        se = int((mi - int(mi)) * 60)
        mi = int(mi)
        dt = datetime(y, m, d, ho, mi, se, tzinfo=UTC)
        loc = dt.astimezone(self.tz)
        return loc

    def set_delta(self, delta, getback=False):
        amount = delta[0]
        what = delta[1]
        dt = datetime.combine(self.ld.date(), self.ld.time())
        if what == 'minutes':
            dt = dt + timedelta(minutes=amount)
        elif what == 'hours':
            dt = dt + timedelta(hours=amount)
        elif what == 'days':
            dt = dt + timedelta(days=amount)
        elif what == 'month':
            change = dt.month+amount
            if change < 1:
                y = dt.year-1; m = 12+change
            elif change > 12:
                y = dt.year+1; m = change-12
            else:
                y = dt.year; m = change
            try:
                dt = dt.replace(year=y, month=m)
            except ValueError:
                try:
                    dt = dt.replace(year=y, month=m, day=dt.day-1)
                except ValueError:
                    dt = dt.replace(year=y, month=m, day=dt.day-2)#February
        elif what == 'year':
            dt = dt.replace(year=(dt.year+amount))
        if not getback:
            self.setdt(dt)
        else:
            return dt

    def dateforcalc(self):
        t = self.dt.time()
        m = t.minute + t.second/60.0
        h = t.hour + m/60.0
        y = self.dt.year
        m = self.dt.month
        d = self.dt.day
        return y, m, d, h

    def dateforstore(self):
        if self.ld.year < 1900:
            y = self.ld.year
            mth = str(self.ld.month).rjust(2,'0')
            day = str(self.ld.day).rjust(2,'0')
            hour = str(self.ld.hour).rjust(2,'0')
            minute = str(self.ld.minute).rjust(2,'0')
            sec = str(self.ld.second).rjust(2,'0')
            zname = self.ld.tzname()
            td = self.ld.utcoffset()
            d, s = td.days, td.seconds
            if d < 0:
                sign = '-'
                s = 86400 - s
            else:
                sign = '+'
            m = s // 60
            h = sign + str(m // 60).rjust(2,'0')
            if m % 60 != 0:
                h += ':'+str(m%60).rjust(2,'0')
            else:
                h += '00'
            strdate = "%s-%s-%sT%s:%s:%s%s%s" % (y, mth, day, hour, minute, sec, h, zname)
            return strdate
        else:
            return self.ld.strftime('%Y-%m-%dT%H:%M:%S%z%Z')

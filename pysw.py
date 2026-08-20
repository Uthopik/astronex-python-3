"""Wrapper sobre pyswisseph que preserva la API histórica del proyecto.

El código del proyecto (chart.py, state.py, directions.py) llama pysw.calc()
esperando una tupla (status, longitud, err_msg). El antiguo _pysw.so retornaba
ese formato; pyswisseph en cambio retorna (xx[6], ret_flag). Este módulo
traduce para que el código de astronex no necesite cambios.

Convenciones preservadas:
- calc(jd, pl, flag) → (status, lon, err_msg)
- calc_ut(jd, pl, flag) → (status, lon, err_msg)
- calc_ut_with_speed(jd, pl, flag) → (status, lon, speed, err_msg)
- houses(jd, lat, lon) → list[12] cúspides Placidus
- planets(jd, flag, p=12) → list[11] longitudes (salta índice 10)
"""
import swisseph as swe


def julday(y, m, d, h):
    gregflag = 0 if (y * 10000 + m * 100 + d) < 15821015 else 1
    return swe.julday(y, m, d, h, gregflag)


def revjul(jd, gregflag=1):
    return swe.revjul(jd, gregflag)


def calc(jd, pl, epheflag=4):
    try:
        xx, ret = swe.calc(jd + delta(jd), pl, epheflag)
        return ret, xx[0], ''
    except swe.Error as e:
        return -1, 0.0, str(e)


def calc_ut(jd, pl, epheflag=4):
    try:
        xx, ret = swe.calc(jd, pl, epheflag)
        return ret, xx[0], ''
    except swe.Error as e:
        return -1, 0.0, str(e)


def calc_ut_with_speed(jd, pl, epheflag=4):
    try:
        xx, ret = swe.calc(jd, pl, epheflag | swe.FLG_SPEED)
        return ret, xx[0], xx[3], ''
    except swe.Error as e:
        return -1, 0.0, 0.0, str(e)


def fixstar(star, jd, epheflag=4):
    return swe.fixstar_ut(star, jd, epheflag)


def houses(jd, glt, glg):
    try:
        cusps, ascmc = swe.houses(jd, glt, glg, b'K')
    except swe.Error:
        # En zona polar Placidus falla; Swiss Ephemeris original cae a
        # Porfirio automaticamente. Imitamos ese comportamiento.
        if glt >= 66.53333336:
            try:
                cusps, ascmc = swe.houses(jd, glt, glg, b'O')
                return list(cusps)
            except swe.Error:
                return None
        print("error computing houses")
        return None
    return list(cusps)


def local_houses(jd, glg, glt, epheflag):
    armc = glg if glg >= 0 else glg + 360
    s, eps, e = calc(jd, -1, epheflag)
    try:
        cusps, ascmc = swe.houses_armc(armc, glt, eps, b'K')
    except swe.Error:
        print("error computing local houses")
        return None
    return list(cusps)


def delta(jd):
    return swe.deltat(jd)


def planets(jd, epheflag, p=12):
    pl = []
    for i in range(p):
        if i == 10:
            continue
        s, l, e = calc(jd, i, epheflag)
        if s < 0:
            print("error: %s" % e)
            return None
        pl.append(l)
    return pl


setpath = swe.set_ephe_path
sidtime = swe.sidtime

#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sys
import os
from optparse import OptionParser

parser = OptionParser()
parser.add_option("-c", "--console", action="store_true", default=False)
(options, args) = parser.parse_args()

# Determinar appath dinámicamente para PyInstaller
if getattr(sys, 'frozen', False):
    # En PyInstaller, los recursos están extraídos en sys._MEIPASS
    appath = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
else:
    # En desarrollo normal, la carpeta actual del script
    appath = os.path.dirname(os.path.abspath(__file__))

from astronex import nex
nex.main(appath, options.console)

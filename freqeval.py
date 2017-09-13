#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Launcher for frequency evaluation program
Allows main code to run as module to allow more consistent imports
Created on 2017/09/03
@author: Nils Nemitz
"""

import sys

from PyQt5.QtWidgets import ( # pylint: disable=locally-disabled, no-name-in-module
    QApplication
)
from PyQt5 import QtGui # pylint: disable=locally-disabled, no-name-in-module
import qdarkstyle


import freqevalgui

if __name__ == '__main__':
    app = QApplication(sys.argv)  # pylint: disable=locally-disabled, invalid-name
    #app.setStyle(QtGui.QStyleFactory.create("Fusion"))
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())
    frame = freqevalgui.FreqEvalMain(app)  # pylint: disable=locally-disabled, invalid-name
    sys.exit(app.exec_())

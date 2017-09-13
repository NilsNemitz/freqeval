#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Constants and definitions for frequency evaluation program 
Created on 2017/09/09
@author: Nils Nemitz
"""

# pylint: disable=locally-disabled, redefined-variable-type
# pylint: disable=locally-disabled, too-many-instance-attributes

#from freqevalgui import GR
from PyQt5.QtGui import ( # pylint: disable=locally-disabled, no-name-in-module
    QColor
    )

class Gr(object):
    """ constants and functions for plotting use """
    WHITE   = QColor(255, 255, 255) # pylint: disable=locally-disabled, bad-whitespace
    GRAY    = QColor(200, 200, 200)
    YELLOW  = QColor(241, 192,  38)
    GREEN   = QColor(166, 215, 112)
    BLUE    = QColor( 87, 187, 187)
    SEA     = QColor( 39, 118, 148)
    PURPLE  = QColor( 92,  98, 214)
    MAGENTA = QColor(214,  73, 183)
    RED     = QColor(230,  55,  55)
    ORANGE  = QColor(213, 121,  19)
    BROWN   = QColor(153,  84,  21) 
    CH_COLS = [SEA, PURPLE, MAGENTA, RED, ORANGE, YELLOW, GREEN, BLUE]

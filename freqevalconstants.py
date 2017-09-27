#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Constants and definitions for frequency evaluation program
Created on 2017/09/09
@author: Nils Nemitz
"""

# py#lint: disable=locally-disabled, redefined-variable-type
# pylint: disable=locally-disabled, too-many-instance-attributes

#from freqevalgui import GR
from PyQt5.QtGui import ( # pylint: disable=locally-disabled, no-name-in-module
    QColor
    )

class Gr(object):
    """ constants and functions for plotting use """
    WHITE    = QColor(255, 255, 255) # pylint: disable=locally-disabled, bad-whitespace
    GRAY     = QColor(200, 200, 200) # pylint: disable=locally-disabled, bad-whitespace
    BLACK    = QColor(  0,   0,   0) # pylint: disable=locally-disabled, bad-whitespace
    YELLOW   = QColor(241, 192,  38) # pylint: disable=locally-disabled, bad-whitespace
    GREEN    = QColor(166, 215, 112) # pylint: disable=locally-disabled, bad-whitespace
    BLUE     = QColor( 87, 187, 187) # pylint: disable=locally-disabled, bad-whitespace
    SEA      = QColor( 39, 118, 148) # pylint: disable=locally-disabled, bad-whitespace
    PURPLE   = QColor( 92,  98, 214) # pylint: disable=locally-disabled, bad-whitespace
    MAGENTA  = QColor(214,  73, 183) # pylint: disable=locally-disabled, bad-whitespace
    RED      = QColor(230,  55,  55) # pylint: disable=locally-disabled, bad-whitespace
    ORANGE   = QColor(213, 121,  19) # pylint: disable=locally-disabled, bad-whitespace
    BROWN    = QColor(153,  84,  21) # pylint: disable=locally-disabled, bad-whitespace
    DK_RED   = QColor(115,  27,  27) # pylint: disable=locally-disabled, bad-whitespace
    DK_GREEN = QColor( 84, 107,  56) # pylint: disable=locally-disabled, bad-whitespace

    #CH_COLS = [SEA, PURPLE, MAGENTA, RED, ORANGE, YELLOW, GREEN, BLUE]

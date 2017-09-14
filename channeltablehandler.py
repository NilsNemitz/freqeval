#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
storage for comb count
Created on Fri Jun  16
@author: Nils
"""

# pylint: disable=locally-disabled, bare-except

from PyQt5 import ( # pylint: disable=locally-disabled, no-name-in-module
    QtCore, Qt
    )

from PyQt5.QtCore import ( # pylint: disable=locally-disabled, no-name-in-module
    Qt
    )

from PyQt5.QtGui import QColor

import numpy as np

from freqevalconstants import Gr # color definitions


class ChannelTableModel(QtCore.QAbstractTableModel):
    """ adjust handling of data in config table """

    COLUMN_NUMBER = 6
    HEADER = (
        "name", "baseline (Hz)", "limit", "corr. (MHz)",
        "ADev ref. (MHz)", "mean value")
    ROW_NUMBER = 4
    ROW_HEADER = ("ch1", "ch2", "ch3", "ch4")

    def __init__(self, parent, *args):
        super().__init__(parent, *args)
        self._data = np.array(
            [('f_CEO',  12000000,   1, True,   100000000, 429e12, np.nan),               # pylint: disable=locally-disabled, bad-whitespace
             ('f_rep',    433500, 300, True,  1000000000,    1e9, 1000000000.123456789), # pylint: disable=locally-disabled, bad-whitespace
             ('Sr beat',58000000, 300, True,    80500000, 429e12, np.nan),                # pylint: disable=locally-disabled, bad-whitespace
             ('In beat', 1500000,   0, False,  130000000, 317e12, np.nan)                 # pylint: disable=locally-disabled, bad-whitespace
            ], dtype=[
                ('name', 'S10'),
                ('base', 'f8'),
                ('band', 'f8'),
                ('filt', 'bool'),
                ('corr', 'f8'),
                ('aref', 'f8'),
                ('mean', 'f8')
            ])
        self._color_list = (
            Gr.SEA,
            Gr.PURPLE,
            Gr.MAGENTA,
            Gr.RED
        )

    def columnCount(self, parent):
        return self.COLUMN_NUMBER

    def rowCount(self, parent):
        return self.ROW_NUMBER

    def headerData(self, col, orientation, role):
        if role != Qt.DisplayRole:
            return None
        if orientation == Qt.Horizontal:
            return self.HEADER[col]
        if orientation == Qt.Vertical:
            return self.ROW_HEADER[col]
        return None

    def flags(self, index):
        col = index.column()
        if col == 0:
            return(
                Qt.ItemIsEnabled
                | Qt.ItemIsSelectable
                | Qt.ItemIsEditable
                )
        elif col == 1:
            return Qt.ItemIsEnabled
        elif col == 2:
            return(
                Qt.ItemIsEnabled
                | Qt.ItemIsSelectable
                | Qt.ItemIsUserCheckable
                | Qt.ItemIsEditable
                )
        elif  col == 3:
            return(
                Qt.ItemIsEnabled
                | Qt.ItemIsSelectable
                | Qt.ItemIsEditable
                )
        elif col == 4:
            return(
                Qt.ItemIsEnabled
                | Qt.ItemIsSelectable
                | Qt.ItemIsEditable
                )
        elif col == 5:
            return Qt.ItemIsEnabled | Qt.ItemIsSelectable
        return Qt.ItemIsEnabled

    def data(self, index, role):
        col = index.column()
        row = index.row()
        if row < 0 or row > self.ROW_NUMBER:
            return None

        if role == Qt.DisplayRole:
            string = "error"
            if col == 0:
                string = self._data[row]['name'].decode('UTF-8')
            elif col == 1: # baseline value
                string = '{:,.0f}'.format(self._data[row]['base'])
            elif col == 2: # filter / allowed band
                string = "{0:{1}>5,.1f}".format(self._data[row]['band']," ")
                # pad with digit-sized space
            elif col == 3: # offset
                string = '{:+,.3f}'.format(self._data[row]['corr']/1000000)
            elif col == 4: # ADev refernce
                string = '{:,.0f}'.format(self._data[row]['aref']/1000000)
            elif col == 5:
                string = "{0:{1}>18,.6f}".format(self._data[row]['mean']," ") 
                # pad with digit-sized space
            return string
        if role == Qt.CheckStateRole:
            if( col == 2):
                if( self._data[row]['filt'] ):
                    return(Qt.Checked)
                else: 
                    return(Qt.Unchecked)
        if role == Qt.TextAlignmentRole:
            if( col == 0):
                return Qt.AlignCenter
            elif( col == 1): # baseline value
                return Qt.AlignRight
            elif( col == 2): # filter / allowed band
                return Qt.AlignLeft
            elif( col == 3): # offset
                return Qt.AlignRight
            elif( col == 4): # ADev reference
                return Qt.AlignRight
            elif( col == 5): # mean
                return Qt.AlignRight

        return None

    def names(self):
        """ getter function for channel filter toggles """
        return self._data['name']

    def filter_state(self):
        """ getter function for channel filter toggles """
        return self._data['filt']

    def baselines(self):
        """ getter function for baseline values """
        return self._data['base']
    
    def bands(self):
        """ getter function for band restriction for unlock filter """
        return self._data['band']

    def adev_ref(self):
        """ getter function for ADev reference value """
        return self._data['aref']

    def set_color_list(self, list):
        return

    def color(self, col):
        if col < 0 or col >= len(self._color_list): 
            return None
        return self._color_list[col]
            

    def set_mean(self, index, value):
        """ setter function for mean value """
        if index < 0 or index >= self.ROW_NUMBER:
            return
        self._data[index]['mean'] = value + self._data[index]['base']

    def print_data(self):
        """ debug print of table status """
        print(self._data['mean'])
        


        

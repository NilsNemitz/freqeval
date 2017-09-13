#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
backend for evaluation matrix table
Created on 2017/09/10
@author: Nils Nemitz
"""

# pylint: disable=locally-disabled, bare-except

from PyQt5 import ( # pylint: disable=locally-disabled, no-name-in-module
    QtCore, Qt
    )

from PyQt5.QtCore import Qt as QtC # pylint: disable=locally-disabled, no-name-in-module
#from PyQt5.QtGui import QColor

import numpy as np

#from freqevalconstants import Gr # color definitions


class EvaluationTableModel(QtCore.QAbstractTableModel):
    """ adjust handling of data in evaluation matrix/table """

    COLUMN_NUMBER = 2
    HEADER = ("strontium", "indium")
    ROW_NUMBER = 9
    ROW_HEADER = (
        "actual frequency",        
        "baseline-subtracted",
        "estim. uncertainty",
        "",
        "ch1 coeff. (f_CEO)",
        "ch2 coeff. (f_rep)",
        "ch3 coeff. (f_Sr)",
        "ch4 coeff. (f_In)",
        "baseline (Hz)"
         )

    def __init__(self, parent, channel_table):
        super().__init__(parent)
        self._channel_table = channel_table
        print("setting up evaluation table with channel table: ",self._channel_table)
        #self._data = np.array(
        #    [('f_CEO', 12000000,   1, True,   100000000, 429e12, np.nan),               # pylint: disable=locally-disabled, bad-whitespace
        #     ('f_rep',   400000, 300, True,  1000000000,    1e9, 1000000000.123456789), # pylint: disable=locally-disabled, bad-whitespace
        #     ('Sr beat',      0,   0, False,   80000000, 429e12, np.nan),                # pylint: disable=locally-disabled, bad-whitespace
        #     ('In beat',1500000,   0, False,  130000000, 317e12, np.nan)                 # pylint: disable=locally-disabled, bad-whitespace
        #    ], dtype=[
        #        ('name', 'S10'),
        #        ('base', 'f8'),
        #        ('band', 'f8'),
        #        ('filt', 'bool'),
        #        ('corr', 'f8'),
        #        ('aref', 'f8'),
        #        ('mean', 'f8')
        #    ])
        #self._color_list = (
        #    Gr.SEA,
        #    Gr.PURPLE,
        #    Gr.MAGENTA,
        #    Gr.RED
        #)

    def columnCount(self, parent):
        return self.COLUMN_NUMBER

    def rowCount(self, parent):
        return self.ROW_NUMBER

    def headerData(self, col, orientation, role):
        if role != QtC.DisplayRole:
            return None
        if orientation == QtC.Horizontal:
            return self.HEADER[col]
        if orientation == QtC.Vertical:
            return self.ROW_HEADER[col]
        return None

    def flags(self, index):
        if not index.isValid():
            return None
        col = index.column()
        return QtC.ItemIsEnabled
        return(
            QtC.ItemIsEnabled
            | QtC.ItemIsSelectable
            | QtC.ItemIsEditable
        )

    def data(self, index, role):
        if not index.isValid():
            return None
        col = index.column()
        row = index.row()

        if role == QtC.DisplayRole:
            return "empty"
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
        if role == QtC.TextAlignmentRole:
            if( col == 0):
                return QtC.AlignCenter
            elif( col == 1): # baseline value
                return QtC.AlignRight
            elif( col == 2): # filter / allowed band
                return QtC.AlignLeft
            elif( col == 3): # offset
                return QtC.AlignRight
            elif( col == 4): # ADev reference
                return QtC.AlignRight
            elif( col == 5): # mean
                return QtC.AlignRight
        if role == QtC.CheckStateRole:
            return None

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
        


        

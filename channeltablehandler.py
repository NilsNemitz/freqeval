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
from PyQt5.QtCore import Qt as QtC # pylint: disable=locally-disabled, no-name-in-module

import numpy as np

# from freqevalconstants import Gr # color definitions

class ChannelTableModel(QtCore.QAbstractTableModel):
    """ adjust handling of data in config table """

    COLUMN_NUMBER = 6
    HEADER = (
        "name", "baseline (Hz)", "limit", "corr. (MHz)",
        "ADev ref. (MHz)", "mean value")

    def __init__(self, parent, logic, *args):
        super().__init__(parent, *args)
        self._logic = logic
        self.parameters = np.array(
            [('f_CEO',   None, 12000000,   1, True,   100000000, 429e12, np.nan),               # pylint: disable=locally-disabled, bad-whitespace
             ('f_rep',   None,   433500, 300, True,  1000000000,    1e9, 1000000000.123456789), # pylint: disable=locally-disabled, bad-whitespace
             ('Sr beat', None, 58000000, 300, True,    80500000, 429e12, np.nan),                # pylint: disable=locally-disabled, bad-whitespace
             ('In beat', None,  1500000,   0, False,  130000000, 317e12, np.nan)                 # pylint: disable=locally-disabled, bad-whitespace
            ], dtype=[
                ('name', 'S10'),
                ('color', 'object'),
                ('base', 'f8'),
                ('tole', 'f8'),
                ('filt', 'bool'),
                ('corr', 'f8'),
                ('aref', 'f8'),
                ('mean', 'f8')
            ])

    #######################################################################
    def set_from_config(self):
        """ sets up table content from config data """
        config = self._logic.config # convenience access
        section = 'CONFIG'
        if not section in self._logic.config:
            self.eval_config[section] = {}
        self.count = config[section].getint('channels', 4)
        # print("trying to resize data array to ", self.count, " channels.")
        if self.count > 0 and self.count <= 32:
            self.parameters.resize(self.count)

        for index in range(self.count):
            section = 'CHANNEL{:d}'.format(index+1)
            if not section in config:
                config[section] = {} # create if not available
            self.parameters[index]['name'] = config[section].get('name', section)
            self.parameters[index]['color'] = self._logic.make_color(
                config[section].get('color', "#999999") # as byte string!
                )
            self.parameters[index]['base'] = config[section].getint('baseline', 0)
            self.parameters[index]['tole'] = config[section].getfloat('tolerance', 0)
            self.parameters[index]['filt'] = config[section].getboolean('filter', False)
            self.parameters[index]['corr'] = config[section].getfloat('correction', 0)
            self.parameters[index]['aref'] = config[section].getfloat('adev_reference', 1)
            self.parameters[index]['mean'] = np.nan

    #######################################################################
    def update_config(self, config):
        """ update values in config object to prepare for saving """

    #######################################################################
    def columnCount(self, parent):
        """ QTableView interface: column number """
        return self.COLUMN_NUMBER

    #######################################################################
    def rowCount(self, parent):
        """ QTableView interface: row number """
        return self.count

    #######################################################################
    def headerData(self, col, orientation, role):
        """ QTableView interface: header text and formatting """
        if role != QtC.DisplayRole:
            return None
        if orientation == QtC.Horizontal:
            return self.HEADER[col]
        if orientation == QtC.Vertical:
            return 'ch {:d}'.format(col+1)
        return None

    #######################################################################
    def flags(self, index):
        """ QTableView interface: select/enable/etc flags """
        col = index.column()
        if col == 0:
            return QtC.ItemIsEnabled | QtC.ItemIsSelectable | QtC.ItemIsEditable
        elif col == 1:
            return QtC.ItemIsEnabled
        elif col == 2:
            return(
                QtC.ItemIsEnabled | QtC.ItemIsSelectable
                | QtC.ItemIsUserCheckable | QtC.ItemIsEditable
                )
        elif  col == 3:
            return QtC.ItemIsEnabled | QtC.ItemIsSelectable | QtC.ItemIsEditable
        elif col == 4:
            return QtC.ItemIsEnabled | QtC.ItemIsSelectable | QtC.ItemIsEditable
        elif col == 5:
            return QtC.ItemIsEnabled | QtC.ItemIsSelectable
        return QtC.ItemIsEnabled

    #######################################################################
    def data(self, index, role):
        """ QTableView interface: main data access """
        if not index.isValid():
            return None
        col = index.column()
        row = index.row()

        if col == 0:
            if role == QtC.DisplayRole:
                string = self.parameters[row]['name'].decode('UTF-8')
                return string
            elif role == QtC.BackgroundColorRole:
                return self.parameters[row]['color']
            elif role == QtC.TextAlignmentRole:
                return QtC.AlignCenter
            return None

        if role == QtC.DisplayRole:
            string = "error"
            if col == 1: # baseline value
                string = '{:,.0f}'.format(self.parameters[row]['base'])
            elif col == 2: # filter / tolerance
                string = "{0:{1}>5,.1f}".format(self.parameters[row]['tole']," ")
                # pad with digit-sized space
            elif col == 3: # offset
                string = '{:+,.3f}'.format(self.parameters[row]['corr']/1000000)
            elif col == 4: # ADev refernce
                string = '{:,.0f}'.format(self.parameters[row]['aref']/1000000)
            elif col == 5:
                string = "{0:{1}>18,.6f}".format(self.parameters[row]['mean']," ") 
                # pad with digit-sized space
            return string
            
        if role == QtC.CheckStateRole:
            if( col == 2):
                if( self.parameters[row]['filt'] ):
                    return(QtC.Checked)
                else: 
                    return(QtC.Unchecked)
        if role == QtC.TextAlignmentRole:
            if( col == 1): # baseline value
                return QtC.AlignRight | QtC.AlignVCenter
            elif( col == 2): # filter / tolerance
                return QtC.AlignLeft | QtC.AlignVCenter
            elif( col == 3): # offset
                return QtC.AlignRight | QtC.AlignVCenter
            elif( col == 4): # ADev reference
                return QtC.AlignRight | QtC.AlignVCenter
            elif( col == 5): # mean
                return QtC.AlignRight | QtC.AlignVCenter

        return None

    #######################################################################
    def set_mean(self, num_index, value):
        """ setter function for mean value """
        if num_index < 0 or num_index >= self.count:
            return
        self.parameters[num_index]['mean'] = value + self.parameters[num_index]['base']

    #######################################################################
    def update_view(self):
        """ initiate redraw """
        index_tl = self.createIndex(0, 0)        
        index_br = self.createIndex(
            self.rowCount(None), 
            self.columnCount(None)
            )        
        self.dataChanged.emit(index_tl,index_br, [QtC.DisplayRole])

    #######################################################################
    def print_data(self):
        """ debug print of table status """
        print(self.parameters['mean'])

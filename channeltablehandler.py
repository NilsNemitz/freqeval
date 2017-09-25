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

from freqevalconstants import Gr # color definitions


class ChannelTableModel(QtCore.QAbstractTableModel):
    """ adjust handling of data in config table """

    COLUMN_NUMBER = 6
    HEADER = (
        "name", "baseline (Hz)", "limit", "corr. (MHz)",
        "ADev ref. (MHz)", "mean value")

    def __init__(self, parent, logic, *args):
        super().__init__(parent, *args)
        self._logic = logic
        self._data = np.array(
            [('f_CEO',  12000000,   1, True,   100000000, 429e12, np.nan),               # pylint: disable=locally-disabled, bad-whitespace
             ('f_rep',    433500, 300, True,  1000000000,    1e9, 1000000000.123456789), # pylint: disable=locally-disabled, bad-whitespace
             ('Sr beat',58000000, 300, True,    80500000, 429e12, np.nan),                # pylint: disable=locally-disabled, bad-whitespace
             ('In beat', 1500000,   0, False,  130000000, 317e12, np.nan)                 # pylint: disable=locally-disabled, bad-whitespace
            ], dtype=[
                ('name', 'S10'),
                ('base', 'f8'),
                ('tole', 'f8'),
                ('filt', 'bool'),
                ('corr', 'f8'),
                ('aref', 'f8'),
                ('mean', 'f8')
            ]) # TODO: convert to python data structure

    #######################################################################
    def set_from_config(self, config):
        """ sets up table content from config data """
        # we are relying on freqevallogic to make sure there are default values
        num_channels = config['CONFIG'].getint('channels', 4)
        print("trying to resize data array to ", num_channels, " channels.")
        if num_channels > 0 and num_channels <= 32:
            self._data.resize(num_channels)

        clist = []
        for index in range(num_channels):
            section = 'CHANNEL{:d}'.format(index+1)
            name = config[section].get('name', section)
            self._data[index]['name'] = name
            col = config[section].get('color', "999999")
            clist.append(col)
            baseline = config[section].getint('baseline', 0)
            self._data[index]['base'] = baseline # TODO: allow only int
            tolerance = config[section].getfloat('tolerance', 0)
            self._data[index]['tole'] = tolerance
            filter_act = config[section].getboolean('filter', False)
            self._data[index]['filt'] = filter_act
            correction = config[section].getfloat('correction', 0)
            self._data[index]['corr'] = correction
            adev_reference = config[section].getfloat('adev_reference', 1)
            self._data[index]['aref'] = adev_reference
            self._data[index]['mean'] = 0

        self._logic.set_channel_color_list(clist)
        return num_channels

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
        return self._logic.num_channels

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
                string = self._data[row]['name'].decode('UTF-8')
                return string
            elif role == QtC.BackgroundColorRole:
                color = self._logic.channel_color_list[row]
                return color
            elif role == QtC.TextAlignmentRole:
                return QtC.AlignCenter
            return None

        if role == QtC.DisplayRole:
            string = "error"
            if col == 1: # baseline value
                string = '{:,.0f}'.format(self._data[row]['base'])
            elif col == 2: # filter / tolerance
                string = "{0:{1}>5,.1f}".format(self._data[row]['tole']," ")
                # pad with digit-sized space
            elif col == 3: # offset
                string = '{:+,.3f}'.format(self._data[row]['corr']/1000000)
            elif col == 4: # ADev refernce
                string = '{:,.0f}'.format(self._data[row]['aref']/1000000)
            elif col == 5:
                string = "{0:{1}>18,.6f}".format(self._data[row]['mean']," ") 
                # pad with digit-sized space
            return string
            
        if role == QtC.CheckStateRole:
            if( col == 2):
                if( self._data[row]['filt'] ):
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
    def names(self):
        """ getter function for channel name """
        return self._data['name']

    #######################################################################
    def filter_state(self):
        """ getter function for channel filter toggles """
        return self._data['filt']

    #######################################################################
    def baselines(self):
        """ getter function for baseline values """
        return self._data['base']
    
    #######################################################################
    def corrections(self):
        """ getter function for correction values """
        return self._data['corr']

    #######################################################################
    def tolerances(self):
        """ getter function for tolerance for unlock filter """
        return self._data['tole']

    #######################################################################
    def adev_ref(self):
        """ getter function for ADev reference value """
        return self._data['aref']

    #######################################################################
    def set_mean(self, num_index, value):
        """ setter function for mean value """
        if num_index < 0 or num_index >= self._logic.num_channels:
            return
        self._data[num_index]['mean'] = value + self._data[num_index]['base']

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
        print(self._data['mean'])
        


        

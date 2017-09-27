#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
table backend for per-channel ADev results
Created on 2017/09/09
@author: Nils Nemitz
"""

# pylint: disable=locally-disabled, bare-except

from PyQt5 import ( # pylint: disable=locally-disabled, no-name-in-module
    QtCore, Qt, QtGui
    )

from PyQt5.QtCore import ( # pylint: disable=locally-disabled, no-name-in-module
    Qt
    )

import numpy as np

class ChannelADevTableModel(QtCore.QAbstractTableModel):
    """ adjust handling of data in config table """

    COLUMN_NUMBER = 5
    HEADER = ("tau (s)", "Ch 1", "Ch 2", "Ch 3", "Ch 4")
    ROW_NUMBER = 4
    ROW_HEADER = ("1", "2", "3", "4")

    def __init__(self, parent, logic):
        super().__init__(parent)
        self._logic = logic

    def columnCount(self, parent):
        return self._logic.channel_table.count

    def rowCount(self, parent):
        return self.ROW_NUMBER

    def headerData(self, col, orientation, role):
        #if (
        #    role != Qt.DisplayRole
        #    and role != Qt.BackgroundColorRole
        #):
        #    return None
        #if role == Qt.DisplayRole:
        #    if orientation == Qt.Horizontal:
        #        #print("getting name for column ",col)
        #        index = self._channel_table.createIndex(col, 0)
        #        name = self._channel_table.data(index, Qt.DisplayRole)
        #        return "ch"+str(col+1)+" ("+name+")"
        #    if orientation == Qt.Vertical:
        #        return self.ROW_HEADER[col]
        #if role == Qt.ForegroundRole and orientation == Qt.Horizontal:
        #    return QtGui.QColor(214, 173, 183)
        return None

    #def flags(self, index):
    #    col = index.column()
    #    if col == 0:
    #        return(
    #            Qt.ItemIsEnabled
    #            | Qt.ItemIsSelectable
    #            | Qt.ItemIsEditable
    #            )
    #    elif col == 1:
    #        return Qt.ItemIsEnabled
    #    elif col == 2:
    #        return(
    #            Qt.ItemIsEnabled
    #            | Qt.ItemIsSelectable
    #            | Qt.ItemIsUserCheckable
    #            | Qt.ItemIsEditable
    #            )
    #    elif  col == 3:
    #        return(
    #            Qt.ItemIsEnabled
    #            | Qt.ItemIsSelectable
    #            | Qt.ItemIsEditable
    #            )
    #    elif col == 4:
    #        return(
    #            Qt.ItemIsEnabled
    #            | Qt.ItemIsSelectable
    #            | Qt.ItemIsEditable
    #            )
    #    elif col == 5:
    #        return Qt.ItemIsEnabled | Qt.ItemIsSelectable
    #    return Qt.ItemIsEnabled

    def data(self, index, role):
        if not index.isValid():
            return None
        col = index.column()
        row = index.row()

        if row == 0:
            if role == Qt.DisplayRole:
                name = self._logic.channel_table.parameters[col]['name'].decode('UTF-8')
                #index = self._logic.channel_table.createIndex(col, 0)
                #name = self._channel_table.data(index, Qt.DisplayRole)
                return "ch"+str(col+1)+" ("+name+")"
                #return
            elif role == Qt.BackgroundColorRole:
                color = self._logic.channel_table.parameters[col]['color']
                return color
                #return QtGui.QColor(214,  73, 183)

        if role == Qt.DisplayRole:
            string = "error"
            # TESTING
            return string
            # TESTING
            if col == 0:
                string = self.data[row]['name'].decode('UTF-8')
            elif col == 1: # baseline value
                string = '{:,.0f}'.format(self.data[row]['base'])
            elif col == 2: # filter / allowed band
                string = "{0:{1}>5,.1f}".format(self.data[row]['band']," ")
                # pad with digit-sized space
            elif col == 3: # offset
                string = '{:+,.3f}'.format(self.data[row]['corr']/1000000)
            elif col == 4: # ADev refernce
                string = '{:,.0f}'.format(self.data[row]['aref']/1000000)
            elif col == 5:
                string = "{0:{1}>18,.6f}".format(self.data[row]['mean']," ") 
                # pad with digit-sized space
            return string
        if role == Qt.CheckStateRole:
            return None
            if( col == 2):
                if( self.data[row]['filt'] ):
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

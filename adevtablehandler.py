#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
table backend for ADev results
Created on 2017/09/09
@author: Nils Nemitz
"""

# pylint: disable=locally-disabled, bare-except

from PyQt5 import ( # pylint: disable=locally-disabled, no-name-in-module
    QtCore, Qt, QtGui
    )

from PyQt5.QtCore import Qt as QtC # pylint: disable=locally-disabled, no-name-in-module


import numpy as np

class ADevTableModel(QtCore.QAbstractTableModel):
    """ adjust handling of data in config table """

    COLUMN_NUMBER = 5
    HEADER = ("tau (s)", "Ch 1", "Ch 2", "Ch 3", "Ch 4")
    ROW_NUMBER = 10
    ROW_HEADER = ("1", "2", "3", "4")

    def __init__(self, parent, logic):
        super().__init__(parent)
        self._logic = logic

        taus_per_decade = 10
        scale = 10**(1/taus_per_decade)        
        self.tau_values = [1]
        real_tau = 1.0        
        while real_tau < 1E9:
            real_tau *= scale
            if int(real_tau) > self.tau_values[-1]:
                self.tau_values.append(int(real_tau))
        last_index = len(self.tau_values)-1
        print(len(self.tau_values))
        self.index_list = [0, 6, 16, 30, 55, 68, last_index]
        display_values = [self.tau_values[i] for i in self.index_list]
        print(display_values)
        
        self.channel_adev = []
        self.evaluation_adev = []
        self.step = 1. # time step = sampling rate
        # print('list of tau values: ', self.tau_values)



    def columnCount(self, parent):
        return self._logic.channel_table.count + self._logic.evaluation_table.count 

    def rowCount(self, parent):
        return self.ROW_NUMBER

    
    #######################################################################
    def headerData(self, col, orientation, role): # pylint: disable=locally-disabled, invalid-name
        """ TableView: return header strings and alignment """
        if orientation != QtC.Vertical:
            return None
        if role == QtC.DisplayRole:
            if col == 0:
                return 'τ (s)'
            if col < 8:
                tau_index = self.index_list[col-1]
                return '{:0,.0f}'.format(self.tau_values[tau_index])
            if col == 8:
                return 'time span'
            if col == 9:
                return 'extrapol.'
        elif role == QtC.TextAlignmentRole:
            return QtC.AlignRight | QtC.AlignVCenter
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
        row = index.row()
        col = index.column()
        ch_col = col
        eval_col = col - self._logic.channel_table.count
        if (ch_col < 0) or (ch_col >= self._logic.channel_table.count):
            ch_col = None
        if (eval_col < 0) or (eval_col >= self._logic.evaluation_table.count):
            eval_col = None
        #print('col: ',col,' --> ',ch_col,'  /  ',eval_col)
        
        if row == 0:
            if role == QtC.DisplayRole:
                if ch_col is not None: 
                    # channel table uses a numpy array for storage
                    name = (
                        'ch' + str(ch_col+1) + ' ('
                        + self._logic.channel_table.parameters[ch_col]['name'].decode('UTF-8')+')'
                    )
                elif eval_col is not None:
                    # evaluation table uses a dictionary
                    name = (
                        'ev' + str(eval_col+1) + ' ('
                        + self._logic.evaluation_table.parameters[eval_col]['name'][0:6]+')'
                        )
                else:
                    name = 'Eval. {:2f}'.format(col+1)
                return name
            elif role == QtC.BackgroundColorRole:
                if ch_col is not None:
                    return self._logic.channel_table.parameters[ch_col]['color']
                elif eval_col  is not None:
                    return self._logic.evaluation_table.parameters[eval_col]['color']
                else:
                    return QtGui.QColor(214,  73, 183)
            elif role == QtC.ForegroundRole:
                return self._logic.BLACK
            elif role == QtC.TextAlignmentRole:
                return QtC.AlignCenter
            return None

        if role == QtC.DisplayRole:
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
        if role == QtC.CheckStateRole:
            return None
            if( col == 2):
                if( self.data[row]['filt'] ):
                    return(QtC.Checked)
                else: 
                    return(QtC.Unchecked)
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

        return None

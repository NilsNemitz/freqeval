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
    ROW_NUMBER = 9
    ROW_HEADER = ("1", "2", "3", "4")

    def __init__(self, parent, logic):
        super().__init__(parent)
        self._logic = logic

        self.channel_adev = {}
        self.channel_ref = {}
        self.evaluation_adev = {}
        self.evaluation_ref = {}
        self.time_step = 1.234 # time step = sampling rate
        self.tau_targets = [1E0, 1E1, 1E2, 1E3, 1E4, 1E5, 1E6, 1E7, 1E8, 1E9]
        self.tau_values = self.tau_targets
        self.tau_index_dict = {}

    def generate_taus(self, time_step):
        """ generate list of tau values for given time step """
        # this aims to create ten values per decade for plotting
        self.time_step = time_step
        del time_step
        TAUS_PER_DECADE = 10
        scale = 10**(1/TAUS_PER_DECADE)
        # these will be reverse indexed and also set the range:

        self.tau_index_dict = {}
        self.tau_values = [0] # will be removed later
        # at low averaging time the list is pruned to avoid duplicates
        real_tau = 0.001
        print('timestep = ', self.time_step)
        rounded_tau = self.time_step * round(real_tau/self.time_step)
        # print('real tau = ', real_tau, ' --> ', rounded_tau)
        for target in self.tau_targets:
            while real_tau < target:
                last_tau = rounded_tau
                real_tau *= scale
                rounded_tau = self.time_step * round(real_tau/self.time_step)
                print('real tau = ', real_tau, ' --> ', rounded_tau)
                if rounded_tau > self.tau_values[-1]:
                    # do not add redunant values to the tau list
                    self.tau_values.append(rounded_tau)
            # now we jumped over a target value:
            key = int(target) # put integer numbers into keys
            if len(self.tau_values) < 2:
                self.tau_index_dict[key] = 0
            elif abs(self.tau_values[-1] - target) < abs(self.tau_values[-2] - target):
                self.tau_index_dict[key] = len(self.tau_values) - 1 - 1 # last element
            else:
                self.tau_index_dict[key] = len(self.tau_values) - 2 - 1 # 2nd-to-last element
        self.tau_values = self.tau_values[1:-1] # drop first dummy element
        print('list of taus: ', self.tau_values)
        print('dictionary of indices of major tau values: ', self.tau_index_dict)

    #######################################################################
    def add_channel_adev(self, index, dataset, reference):
        """ channel: store dataset object generated by Allantools """
        self.channel_adev[index] = dataset
        self.channel_ref[index] = reference

    #######################################################################
    def add_evalulation_adev(self, index, dataset, reference):
        """ evaluation: store dataset object generated by Allantools """
        self.evaluation_adev[index] = dataset
        self.evaluation_ref[index] = reference

    #######################################################################
    # table data interface used by QTableView
    #######################################################################
    def columnCount(self, parent):
        return self._logic.channel_table.count + self._logic.evaluation_table.count

    #######################################################################
    def rowCount(self, parent):
        return self.ROW_NUMBER

    #######################################################################
    def headerData(self, row, orientation, role): # pylint: disable=locally-disabled, invalid-name
        """ TableView: return header strings and alignment """
        if orientation != QtC.Vertical:
            return None
        if role == QtC.DisplayRole:
            if row == 0:
                return 'τ (s)'
            if row < self.ROW_NUMBER-2:
                target_index = row - 1
                try:
                    target_key = int(self.tau_targets[target_index])
                    index = self.tau_index_dict[target_key]
                    return '{:0,.1f}'.format(self.tau_values[index])
                except (IndexError, KeyError) as exception:
                    return 'undefined'
            if row == self.ROW_NUMBER-2:
                return 'time span'
            if row == self.ROW_NUMBER-1:
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


#
#            (taus_used, adev, adeverror, adev_n) = allantools.oadev(
#                values, data_type='freq', rate=self.time_step, taus='decade'
#                )

#            # scale to fractional values according to table settings
#            adev /= reference_values[ch_index]
#            adeverror /= reference_values[ch_index]
            #print('channel index: ', index)
            #print('taus: ',taus_used)
            #print('adev: ',adev)
            #print("adeverror: ",adeverror)
#            del adev_n
#            new_adev_obj.add_data(ch_index, taus_used, adev, adeverror)
#        #update overall adev object
#        # TODO: error handling / consistency check?
#        self.ch_adev = new_adev_obj



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
                    return QtGui.QColor(214, 73, 183)
            elif role == QtC.ForegroundRole:
                return self._logic.BLACK
            elif role == QtC.TextAlignmentRole:
                return QtC.AlignCenter
            return None

        if role == QtC.DisplayRole:
            if row < self.ROW_NUMBER-2:
                if ch_col is not None:
                    try:
                        adev = self.channel_adev[ch_col].out
                    except KeyError as exception:
                        return 'ch. undef.'
                else:
                    return '(eval)'
                target_index = row - 1
                try:
                    target_key = int(self.tau_targets[target_index])
                    index = self.tau_index_dict[target_key]
                    return '{:5.1e} +- X'.format(
                        adev['stat'][index]
                        )
                except (IndexError, KeyError) as exception:
                    return 'undefined'
            if row == self.ROW_NUMBER-2:
                return 'time span'
            if row == self.ROW_NUMBER-1:
                return 'extrapol.'
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

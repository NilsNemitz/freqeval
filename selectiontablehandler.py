#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
table model for point selection in frequency evaluation program
Created on 2017/09/23
@author: Nils Nemitz
"""

# pylint: disable=locally-disabled, bare-except

from datetime import datetime #, timezone

from PyQt5 import ( # pylint: disable=locally-disabled, no-name-in-module
    QtCore, Qt
    #pyqtsignal
    )
from PyQt5.QtCore import Qt as QtC # pylint: disable=locally-disabled, no-name-in-module
from PyQt5.QtCore import pyqtSignal

from jdcal import gcal2jd #, jd2gcal #, MJD_0

#######################################################################
#######################################################################
class TimeStore:
    """ convenience storage object for reference, start and end time """
    def __init__(self, tzero):
        self.val = 0
        self.str = '23:42:00.1'
        self.day = 580003
        self.tzero = tzero # offset from normal epoch

#######################################################################
    def as_mjd_from_time(self, time):
        """ set string value and day as MJD, used for display of tmin """
        self.val = time
        date = datetime.utcfromtimestamp(time)
        self.str = '{:02.0f}:{:02.0f}:{:02.0f}.{:1.0f}'.format(
            date.hour, date.minute, date.second, date.microsecond/100000
        )
        mjd0, mjd = gcal2jd(date.year, date.month, date.day)
        del mjd0
        self.day = mjd

#######################################################################
    def from_time(self, time):
        """ set from relative time stamp value """
        self.val = time
        date = datetime.utcfromtimestamp(time + self.tzero)
        self.str = '{:02.0f}:{:02.0f}:{:02.0f}.{:1.0f}'.format(
            date.hour, date.minute, date.second, date.microsecond/100000
            )
        self.day = time // 86400


#######################################################################
#######################################################################
class SelectionTableModel(QtCore.QAbstractTableModel):
    """ adjust handling of data in selection table """

    COLUMN_NUMBER = 3
    ROW_NUMBER = 3
    HEADER = ('timestamp', 'UTC time', 'day')
    VHEADER = ('ref.', 'start', 'end')

    def __init__(self, parent, logic, *args):
        super().__init__(parent, *args)
        #self._data_changed = pyqtSignal(QtCore.QModelIndex, QtCore.QModelIndex)
        #print('signal: ',self.dataChanged)
        #print('signal: ',self.dataChanged.emit)

        self._logic = logic

        self._tmin = TimeStore(0)
        self._tmin.as_mjd_from_time(1234567890.1)
        self._tstart = TimeStore(0)
        self._tend = TimeStore(0)
        self._time_a = self._time_b = 0

    #######################################################################
    def clear(self):
        """ clear data """
        for time_store in (self._tmin, self._tstart, self._tend):
            time_store.val = 0
            time_store.str = ''
            time_store.day = 0

    #######################################################################
    def set_tmin(self, tmin):
        """ store zero time offset on loading new file """
        self._tmin.as_mjd_from_time(tmin)
        # reallocate start and end time with proper offset
        self._tstart = TimeStore(tmin)
        self._tstart.from_time(0)
        self._tend = TimeStore(tmin)
        self._tend.from_time(0)
        index_tl = self.createIndex(0, 0)        
        index_br = self.createIndex(self.ROW_NUMBER, self.COLUMN_NUMBER)
        self.dataChanged.emit(index_tl,index_br, [QtC.DisplayRole])
        return self._tmin.day  # returns MJD value of start time

    #######################################################################
    def set_selection(self, t_sel):
        """ update selection markers and displayed information on point selection """
        self._time_b = self._time_a
        self._time_a = t_sel
        if self._time_a < self._time_b:
            # new selection goes before old selection
            self._tstart.from_time(self._time_a)
            self._tend.from_time(self._time_b)
        else:
            self._tend.from_time(self._time_a)
            self._tstart.from_time(self._time_b)

        self.update_view()
        #index_tl = self.createIndex(0, 0)        
        #index_br = self.createIndex(self.ROW_NUMBER, self.COLUMN_NUMBER)
        #self.dataChanged.emit(index_tl,index_br, [QtC.DisplayRole])

    #######################################################################
    def selected_range(self):
        """ return selected range """
        return(self._tstart.val, self._tend.val)

    #######################################################################
#    def set_from_config(self, config):
#        """ sets up table content from config data """
#        # we are relying on freqevallogic to make sure there are default values
#        num_channels = config['CONFIG'].getint('channels', 4)
#        print("trying to resize data array to ", num_channels, " channels.")
#        if num_channels > 0 and num_channels <= 32:
#            self._data.resize(num_channels)
#
#        clist = []
#        for index in range(num_channels):
#            section = 'CHANNEL{:d}'.format(index+1)
#            name = config[section].get('name', section)
#            self._data[index]['name'] = name
#            col = config[section].get('color', "999999")
#            clist.append(col)
#            baseline = config[section].getint('baseline', 0)
#            self._data[index]['base'] = baseline # TODO: allow only int
#            tolerance = config[section].getfloat('tolerance', 0)
#            self._data[index]['tole'] = tolerance
#            filter_act = config[section].getboolean('filter', False)
#            self._data[index]['filt'] = filter_act
#            correction = config[section].getfloat('correction', 0)
#            self._data[index]['corr'] = correction
#            adev_reference = config[section].getfloat('adev_reference', 1)
#            self._data[index]['aref'] = adev_reference
#            self._data[index]['mean'] = 0
#
#        self._logic.set_channel_color_list(clist)
#        return num_channels
#
#    #######################################################################
#    def update_config(self, config):
#        """ update values in config object to prepare for saving """
#
    #######################################################################
    def columnCount(self, parent): # pylint: disable=locally-disabled, invalid-name
        """ QTableView interface: column number """
        del parent
        return self.COLUMN_NUMBER

    #######################################################################
    def rowCount(self, parent): # pylint: disable=locally-disabled, invalid-name
        """ QTableView interface: row number """
        del parent
        return self.ROW_NUMBER

    #######################################################################
    def headerData(self, col, orientation, role): # pylint: disable=locally-disabled, invalid-name
        """ QTableView interface: header text and formatting """
        if role != QtC.DisplayRole:
            return None
        if orientation == QtC.Horizontal:
            return self.HEADER[col]
        if orientation == QtC.Vertical:
            return self.VHEADER[col]
        return None

    #######################################################################
    def flags(self, index):
        """ QTableView interface: select/enable/etc flags """
        if not index.isValid():
            return None
        return QtC.ItemIsEnabled | QtC.ItemIsSelectable # | QtC.ItemIsEditable
        # col = index.column()

    #######################################################################
    def data(self, index, role):
        """ QTableView interface: main data access """
        if not index.isValid():
            return None
        col = index.column()
        row = index.row()
        if role == QtC.TextAlignmentRole:
            return QtC.AlignCenter | QtC.AlignRight
        if role == QtC.DisplayRole:
            time_store = None
            if row == 0:
                time_store = self._tmin
            elif row == 1:
                time_store = self._tstart
            elif row == 2:
                time_store = self._tend
            else:
                return None

            if col == 0:
                return '{:12.1f}'.format(time_store.val)
            elif col == 1:
                return time_store.str
            elif col == 2:
                return '{:5.0f}'.format(time_store.day)
        return None

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
#    def names(self):
#        """ getter function for channel name """
#        return self._data['name']

    #######################################################################
#    def filter_state(self):
#        """ getter function for channel filter toggles """
#        return self._data['filt']

    #######################################################################
#    def baselines(self):
#        """ getter function for baseline values """
#        return self._data['base']

    #######################################################################
#    def corrections(self):
#        """ getter function for correction values """
#        return self._data['corr']

    #######################################################################
#    def tolerances(self):
#        """ getter function for tolerance for unlock filter """
#        return self._data['tole']

    #######################################################################
#    def adev_ref(self):
#        """ getter function for ADev reference value """
#        return self._data['aref']

    #######################################################################
#    def set_mean(self, num_index, value):
#        """ setter function for mean value """
#        if num_index < 0 or num_index >= self._logic.num_channels:
#            return
#        self._data[num_index]['mean'] = value + self._data[num_index]['base']

    #######################################################################
#    def print_data(self):
#        """ debug print of table status """
#        print(self._data['mean'])

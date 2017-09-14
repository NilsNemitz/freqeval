#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
storage for comb count
Created on Fri Jun  16
@author: Nils
"""

# pylint: disable=locally-disabled, bare-except, too-few-public-methods
# pylint: disable=locally-disabled, too-many-locals
import math
import pandas
import numpy as np
import allantools

from freqevalinternal import ADevData

class COL(object):
    """ constants for readable addressing of data columns """
    STAT = 1 # pylint: disable=locally-disabled, bad-whitespace
    TIME = 2 # pylint: disable=locally-disabled, bad-whitespace
    CH1  = 3 # pylint: disable=locally-disabled, bad-whitespace
    CH2  = 4 # pylint: disable=locally-disabled, bad-whitespace
    CH3  = 5 # pylint: disable=locally-disabled, bad-whitespace
    CH4  = 6 # pylint: disable=locally-disabled, bad-whitespace
    FLAG = 7 # pylint: disable=locally-disabled, bad-whitespace
    COLS = [CH1, CH2, CH3, CH4]
    # maps zero-based indices to offset indices in full data array
    CHANNELS = 4


class DataHandler(object): # pylint: disable=locally-disabled, too-many-instance-attributes
    """manage frequency data loading/streaming"""
    def __init__(self, logic):
        super().__init__()

        self._logic = logic
        self._channel_table = self._logic.channel_table

        self._data = None
        self._empty = True
        self._ch_adev_obj = None
        self._tday = 0
        self._tmin = 0
        self._baselines = [0] * 4
        self._overhangs = [1, 10] # points marked bad before/after "out-of-band" point
        self._threshold = 10


    def load_file(self, filename):
        """load data from a frequency csv file"""
        col_names = ['tstr', 'stat', 'time', 'frq1', 'frq2', 'frq3', 'frq4']
        data_frame = pandas.read_csv(
            filename,
            #'C:\\d\prog\\data\\20170831 lock test\\freq_MJD_57997_edited.csv',
            header=0, names=col_names,
            dtype={ # pylint: disable=locally-disabled, no-member
                'tstr': str,
                'stat': str,
                'time': np.float64,
                'frq1': np.float64,
                'frq2': np.float64,
                'frq3': np.float64,
                'frq4': np.float64
                }
            )
        # print(df.dtypes)
        self._data = data_frame.as_matrix() # pylint: disable=locally-disabled, no-member
        del data_frame
        # print(self.data[:, COL.STAT])

        # append a new column of uint8 zeros to indicate deletion flags
        npstatval = np.zeros(self._data.shape[0], dtype=np.uint8, order='C')
        self._data = np.c_[self._data, npstatval]
        for row in self._data:
            if row[COL.STAT].strip() != 'GOOD':
                row[COL.FLAG] = 1

        self._tday = math.floor(min(self._data[:, COL.TIME])/86400)
        self._tmin = self._tday * 86400
        min(self._data[:, COL.TIME])
        print("minimum time: ", self._tmin, " ( = ", self._tday, " days since epoch )")

        self._data[:, COL.TIME] -= self._tmin

        baselines = self._channel_table.baselines()
        print("baselines: ", baselines)

        for index in range(COL.CHANNELS):
            self._data[:, COL.COLS[index]] -= baselines[index]

        tolerances = self._channel_table.tolerances()
        # print("tolerances: ", tolerances)
        filters = self._channel_table.filter_state()
        # print("apply filters: ", filters)
        self.filter_unlocked(tolerances, filters, self._overhangs)
        self.filter_outliers(self._threshold, filters)

        new_adev_obj = self.evaluate_data()
        if new_adev_obj:
            self._ch_adev_obj = new_adev_obj

        return len(self._data)


    ########################################################################################
    def filter_unlocked(self, bands, filter_channels, overhang):
        """ mark where points are out of specified bands """
        block_cnt = 0
        block_forward   = overhang[0]     # pylint: disable=locally-disabled, bad-whitespace
        block_backwards = overhang[1]

        if len(filter_channels) != COL.CHANNELS:
            print("Need channel filter selection for ", COL.CHANNELS, " channels.")
            return -1

        if len(bands) != COL.CHANNELS:
            print("Need band specification for ", COL.CHANNELS, " channels.")
            return -1

        for row in self._data:
            ch1_bad = (filter_channels[0] and abs(row[COL.CH1]) > bands[0])
            ch2_bad = (filter_channels[1] and abs(row[COL.CH2]) > bands[1])
            ch3_bad = (filter_channels[2] and abs(row[COL.CH3]) > bands[2])
            ch4_bad = (filter_channels[3] and abs(row[COL.CH4]) > bands[3])

            if ch1_bad or ch2_bad or ch3_bad or ch4_bad: # pylint: disable=locally-disabled, bad-whitespace
                block_cnt = block_forward+1
            if block_cnt > 0:
                block_cnt -= 1
                row[COL.FLAG] |= 0x02

        block_cnt = 0
        for row in self._data[::-1]:
            if row[COL.FLAG] & 0x02 != 0:
                block_cnt = block_backwards+1
            if block_cnt > 0:
                block_cnt -= 1
                row[COL.FLAG] |= 0x02

    ########################################################################################
    def filter_outliers(self, threshold_factor, filter_channels):
        """ outlier/glitch detection """
        bool_list = self._data[:, COL.FLAG] == 0
        good = self._data[bool_list]
        length = good.shape[0]
        splits = round(length/600)
        if splits < 1:
            return
        good_subarrays = np.array_split(good, splits) # split into rough 600s blocks

        for index in range(COL.CHANNELS):
            if not filter_channels[index]:
                continue
            meanlist = np.zeros(splits)
            varlist = np.zeros(splits)
            col_idx = COL.COLS[index]
            for cnt in range(splits):
                meanlist[cnt] = np.mean(good_subarrays[cnt][:, col_idx])
                varlist[cnt] = np.var(good_subarrays[cnt][:, col_idx])
                #print("   (", index, ") ", meanlist[cnt], "+-", varlist[cnt], " Hz")

            bool_list = (varlist == 0)
            temp = varlist
            temp[bool_list] = 1 # avoid divide by zero.
            mean = np.average(meanlist, weights=1/temp)
            var = np.average(varlist, weights=1/temp)
            sdev = math.sqrt(var)
            lim = sdev * threshold_factor
            # print("weigthed: ",mean, "+-", sdev, " Hz")

            for row in self._data:
                if abs(row[col_idx]-mean) > lim:
                    row[COL.FLAG] |= 0x04

        # repeat one more time
        bool_list = self._data[:, COL.FLAG] == 0
        good = self._data[bool_list]
        length = good.shape[0]
        splits = round(length/600)
        if splits < 1:
            return
        good_subarrays = np.array_split(good, splits) # split into rough 600s blocks

        for index in range(COL.CHANNELS):
            if not filter_channels[index]:
                continue
            print("outlier filter on channel ", index)
        
            meanlist = np.zeros(splits)
            varlist = np.zeros(splits)
            col_idx = COL.COLS[index]
            for cnt in range(splits):
                meanlist[cnt] = np.mean(good_subarrays[cnt][:, col_idx])
                varlist[cnt] = np.var(good_subarrays[cnt][:, col_idx])
                # print("   (", index, ") ", meanlist[cnt], "+-", varlist[cnt], " Hz")
            bool_list = (varlist == 0)
            temp = varlist
            temp[bool_list] = 1 # avoid divide by zero.
            mean = np.average(meanlist, weights=1/temp)
            var = np.average(varlist, weights=1/temp)
            sdev = math.sqrt(var)
            lim = sdev * threshold_factor
            # print("weigthed: ",mean,"+-",sdev," Hz")
            for row in self._data:
                if abs(row[col_idx]-mean) > lim:
                    row[COL.FLAG] |= 0x04

        block_count = 0
        rows = self._data.shape[0]
        print("rows: ", rows)
        if rows >= 2:
            for rowindex in range(rows-1):
                if (self._data[rowindex+1, COL.FLAG] & 0x04):
                    # also flag preceding and following points
                    self._data[rowindex, COL.FLAG] |= 0x04
                    block_count = 2
                else:
                    if block_count > 0:
                        block_count -= 1
                        self._data[rowindex, COL.FLAG] |= 0x04

    ########################################################################################
    def get_good_points(self):
        """ get only points marked as good """
        bool_list = self._data[:, COL.FLAG] == 0
        return self._data[bool_list]

    def get_rej1_points(self):
        """ get points marked as rej1, by being flagged in original data file """
        bool_list = (
            (self._data[:, COL.FLAG] & 0x01 != 0)
            & (self._data[:, COL.FLAG] & 0x10 == 0)
        ) # do not add points already marked as "masked"
        return self._data[bool_list]

    def get_rej2_points(self):
        """ get points marked as rej2, by being far out of range """
        bool_list = (
            (self._data[:, COL.FLAG] & 0x02 != 0)
            & (self._data[:, COL.FLAG] & (0x10+0x01) == 0)
        ) # do not add points already marked as "masked" or "flagged"
        return self._data[bool_list]

    def get_rej3_points(self):
        """ get points marked as rej1, by being X sigma outliers """
        bool_list = (
            (self._data[:, COL.FLAG] & 0x04 != 0)
            & (self._data[:, COL.FLAG] & (0x10+0x02+0x01) == 0)
        ) # do not add points already marked as "masked, flagged" or "unlocked"
        return self._data[bool_list]

    def get_mskd_points(self):
        """ get points manually masked out """
        bool_list = (
            (self._data[:, COL.FLAG] & 0x10 != 0)
        )
        return self._data[bool_list]


    ########################################################################################
    def evaluate_data(self):
        """ evaluate filtered data """
        good = self.get_good_points()
        new_adev_obj = ADevData(COL.CHANNELS) # make new object to store ADev data
        reference_values = self._channel_table.adev_ref()

        for index in range(COL.CHANNELS):
            values = good[:, COL.COLS[index]]
            meanval = np.mean(values)
            # print("mean of channel ",index+1," is ",meanval)
            self._channel_table.set_mean(index, meanval)
            # self.channel_table.print_data()
            # TODO: extract from data, adjust for deadtime?
            rate = 1 # one datapoint per second
            (taus_used, adev, adeverror, adev_n) = allantools.oadev(
                values, data_type='freq', rate=rate, taus='decade'
                )
            # scale to fractional values according to table settings
            adev /= reference_values[index]
            adeverror /= reference_values[index]
            #print('channel index: ', index)
            #print('taus: ',taus_used)
            #print('adev: ',adev)
            #print("adeverror: ",adeverror)
            del adev_n
            new_adev_obj.add_data(index, taus_used, adev, adeverror)
        #update overall adev object
        # TODO: error handling / consistency check?
        self._ch_adev_obj = new_adev_obj

    def channel_adev(self):
        """ get ADev data object used for single channel data """
        return self._ch_adev_obj
        #print("adev_n",adev_n)

    def channels(self):
        """ return number of channels in use """
        return COL.CHANNELS


if __name__ == '__main__':
    print("test")

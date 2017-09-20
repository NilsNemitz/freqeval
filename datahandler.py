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

        # append a new column of uint16 zeros to indicate status flags
        # "status flag" format (True values indicate rejected data)
        # bits  0 -  7: overall channel rejection flags, used in final selection
        # bits  8 - 15: individual channel filter rejection flags
        # bits 16 - 23: global filter rejection flags (transfered from CEO and frep)
        # bits 24 - 31: mask indication, used to display manually rejected data
        npstatval = np.zeros(self._data.shape[0], dtype=np.uint32, order='C')
        self._data = np.c_[self._data, npstatval]
        for row in self._data:
            if row[COL.STAT].strip() != 'GOOD':
                row[COL.FLAG] = 1
                flag = 0x11111111
                row[COL.FLAG] |= flag << 16 # all channel reject for flagged bad data
                row[COL.FLAG] |= flag << 0 # all channel reject for flagged bad data

        self._tday = math.floor(min(self._data[:, COL.TIME])/86400)
        self._tmin = self._tday * 86400
        min(self._data[:, COL.TIME])
        print("minimum time: ", self._tmin, " ( = ", self._tday, " days since epoch )")

        self._data[:, COL.TIME] -= self._tmin

        baselines = self._channel_table.baselines()
        print("baselines: ", baselines)

        # TODO: can this be handled in a way that allows changing it for already loaded data?
        for index in range(COL.CHANNELS):
            self._data[:, COL.COLS[index]] -= baselines[index]
        
        return len(self._data)



    def filter_data(self, overhangs, threshold):
        """ reset data filters (except mask) and re-apply """
        bitmask = 0xFF000000

        for row in self._data:
            # clear everything except manual mask bits, update overall flags
            row[COL.FLAG] &= bitmask
            row[COL.FLAG] |= row[COL.FLAG] >> 24
        
        tolerances = self._channel_table.tolerances()
        # print("tolerances: ", tolerances)
        is_critical = self._channel_table.filter_state()
        # print("apply filters: ", filters)
        self.filter_unlocked(tolerances, is_critical, overhangs)
        self.filter_outliers(threshold, is_critical, overhangs)
        self.filter_gather_results()

        new_adev_obj = self.evaluate_data()
        if new_adev_obj:
            self._ch_adev_obj = new_adev_obj


    def load_maskfile(self, maskfile):
        """load data from a frequency csv file"""
        col_names = ['chan', 'time', 'span']
        maskdata = pandas.read_csv(
            maskfile,
            header=0, names=col_names,
            engine='c',
            error_bad_lines=False,
            warn_bad_lines=True,
            converters={"chan": lambda x: int(x, 16)}
        )

        
        # force to numeric values, adding NaN when conversion is not possible.
        maskdata = maskdata.apply(pandas.to_numeric, errors='coerce')
        maskdata = maskdata.sort_values(by='time') # puts NaN values at the back
        maskdata = maskdata.reset_index(drop=True)
        print(maskdata)
        postponed_indices = []

        if len(maskdata)==0:
            # print("mask file not found or empty.")
            return False

        length = len(self._data)
        print("data length: ",length)
        data_index = 0
        mask_count = 0
        end_time = -1E20
        print( maskdata)
        for mask_index in range(len(maskdata)):
            # print('mask: ',mask_index)
            # need to apply same correction as applied to main time stamps!
            prev_end_time = end_time
            start_time = maskdata['time'][mask_index] - self._tmin
            if start_time < prev_end_time:
                print('mask blocks overlap, postponing:', mask_index)
                print(
                    '  > ', maskdata['chan'][mask_index], ' - ',
                    maskdata['time'][mask_index], ' - ',
                    maskdata['span'][mask_index], ' <'
                    )

                postponed_indices.append(mask_index)
                mask_index += 1
            if not math.isnan(maskdata['span'][mask_index]):
                end_time = start_time + maskdata['span'][mask_index]
            else:
                end_time = start_time + 0.050
            if not math.isnan(maskdata['chan'][mask_index]):
                channel_mask = 0xFF & maskdata['chan'][mask_index]
            else:
                channel_mask = 0x00
            print('mask block ',mask_index, '(',channel_mask,')   from ', start_time, ' to ', end_time)
                

            while(
                data_index < length
                and self._data[data_index, COL.TIME] < start_time
            ):                
                data_index += 1
            while(
                data_index < length
                and self._data[data_index, COL.TIME] < end_time
            ):
                self._data[data_index, COL.FLAG] |= channel_mask << 24
                mask_count += 1
                data_index += 1

        print('masked ',mask_count,' data points.')
        print('maskdata:  ',maskdata)
        print('postponed: ',postponed_indices)
        maskdata2 = maskdata.iloc[postponed_indices,:]
        maskdata = maskdata2.reset_index(drop=True)
        print('maskdata: ',maskdata)
        
        # TODO: add while loop until all postponed data is processed




        #print('loaded mask file.')
        #maskdata.convert_objects(convert_numeric=True)
        #for index in range(len(maskdata)):
        #    print(
        #        'block: ', 
        #        maskdata[index,'time'], ' + ', maskdata[index, 'span'],
        #        ' is type ', repr(maskdata['time',index])
        #        )
        
            

    ########################################################################################
    def filter_unlocked(self, bands, is_critical, overhang):
        """ mark where points are out of specified bands """
        block_cnt = 0
        block_forward   = overhang[0]     # pylint: disable=locally-disabled, bad-whitespace
        block_backwards = overhang[1]

        if len(is_critical) != COL.CHANNELS:
            print("Need critical channel selection for ", COL.CHANNELS, " channels.")
            return -1

        if len(bands) != COL.CHANNELS:
            print("Need band specification for ", COL.CHANNELS, " channels.")
            return -1

        for ch_index in range(COL.CHANNELS):
            flag_bit = (1 << ch_index) << 8 # flag bit for single-channel filter-rejection
            block_cnt = 0
            for row in self._data:
                # locate out-of_band data
                if abs(row[COL.CH1+ch_index]) > bands[ch_index]:
                    block_cnt = block_forward+1
                # extend rejected data according to forward overhand:
                if block_cnt > 0:
                    block_cnt -= 1
                    # set individual channel rejection flag:
                    row[COL.FLAG] |= flag_bit
            # second, backwards pass to extend rejected data according to backwards overhang
            block_cnt = 0
            for row in self._data[::-1]:
                if row[COL.FLAG] & flag_bit != 0:
                    block_cnt = block_backwards+1
                if block_cnt > 0:
                    block_cnt -= 1
                    row[COL.FLAG] |= flag_bit # set filter-rejected flag

            # for critical channels (fCEO and frep), transfer rejection to all channels
            if is_critical[ch_index]:
                for row in self._data:
                    if row[COL.FLAG] & flag_bit != 0:
                        row[COL.FLAG] |= 0b11111111 << 16 # flag all channels as bad-by-transfer


    ########################################################################################
    def filter_outliers(self, threshold_factor, is_critical, overhang):
        """ outlier/glitch detection """
        # TODO: extend to better handle data with drift
        for ch_index in range(COL.CHANNELS):
            freq_data = self._data[:,COL.CH1+ch_index]
            
            ch_flag = 1 << ch_index
            combined_mask = (
                ch_flag
                | ch_flag << 8
                | ch_flag << 16
                | ch_flag << 24
            )
            #print('outliers: channel ',ch_index,' ---> ',combined_mask)
            pick_list = self._data[:, COL.FLAG] & combined_mask == 0
            freq_good = freq_data[pick_list]
            length = freq_good.shape[0]
            #print('size of selected data: ',length)
            if length < 100:
                continue # no remaining data
            splits = math.ceil(length/300)
            block_length = math.ceil(length/splits)
            #print('actual block length: ',block_length)
            meanlist = np.zeros(splits)
            varlist = np.zeros(splits)
            end_index = -1
            for block in range(splits):
                start_index = end_index + 1
                end_index += block_length 
                if end_index >= length:
                    end_index = length # should be -1 ?
                varlist[block] = np.var(freq_good[start_index:end_index])
                # print("   (", block, ") ", meanlist[cnt], "+-", varlist[cnt], " Hz")

            varlist[ (varlist == 0) ] = 1E6 # avoid divide by zero.
            var = np.average(varlist, weights=1/varlist)
            lim = math.sqrt(var) * threshold_factor
            #print("weigthed mean of variance: ",var, " --> ", math.sqrt(var), " Hz")

            # compare data to local mean, constrain to "good" limit of deviation
            width = 2 # total block to average: center element plus X on each side
            elements = 2 * width + 1
            freq_filt = np.convolve(freq_data, np.ones((elements,))/elements, mode='same')
            # left edge of data uses first full block average
            for index in range(0, width):
                if abs(freq_data[index]-freq_filt[width]) > lim:
                    self._data[index, COL.FLAG] |= ch_flag << 8
            # main region uses a sliding window average 
            for index in range(width,len(freq_data)-width):
                if abs(freq_data[index]-freq_filt[index]) > lim:
                    self._data[index, COL.FLAG] |= ch_flag << 8
            # left edge of data uses last full block average
            for index in range(len(freq_data)-width, len(freq_data)):
#                print('R (',index,')  ',freq_data[index],' <--> ',block_mean)                
                if abs(freq_data[index]-freq_filt[len(freq_data)-width-1]) > lim:
                    self._data[index, COL.FLAG] |= ch_flag << 8

            # for critical channels (fCEO and frep), transfer rejection to all channels
            if is_critical[ch_index]:
                flag_bit = ch_flag << 8
                for row in self._data:
                    if row[COL.FLAG] & flag_bit != 0:
                        row[COL.FLAG] |= 0b11111111 << 16 # flag all channels as bad-by-transfer


    ########################################################################################
    def filter_gather_results(self):
        """ gather all individual rejections into merged convenience flag """
        for ch_index in range(COL.CHANNELS):
            for row in self._data:
                masked_flags = (row[COL.FLAG] >> 24) & 0xFF
                transfered_flags = (row[COL.FLAG] >> 16) & 0xFF
                filtered_flags = (row[COL.FLAG] >> 8) & 0xFF
                gathered_flags = masked_flags | transfered_flags | filtered_flags
                row[COL.FLAG] &= 0xFFFFFF00 # clear old flag bits
                row[COL.FLAG] |= gathered_flags # set new gathered flags
                #print("   (", block, ") ", meanlist[cnt], "+-", varlist[cnt], " Hz")

    ########################################################################################
    def get_good_points(self, channel_list):
        """ get only points marked as good for all test_channels in list """
        channel_mask = 0
        col_list = [COL.TIME]
        for channel in channel_list:
            if channel >= COL.CHANNELS:
                print('channel specification ',channel,' exceeds number of channel (',COL.CHANNELS,')')
                return None
            channel_mask |= 1 << channel # look only at gathered flag
            col_list.append(COL.CH1+channel)
        #print('list of columns: ',col_list)
#        col_data = self._data[:, (COL.TIME, COL.CH1+channel)]
        col_data = self._data[:, col_list]
        pick_list = self._data[:, COL.FLAG] & channel_mask == 0
        return col_data[pick_list]

    def get_mskd_points(self, channel):
        if channel >= COL.CHANNELS:
            print('channel specification ',channel,' exceeds number of channel (',COL.CHANNELS,')')
            return None
        col_data = self._data[:, (COL.TIME, COL.CH1+channel)]
        test_flag = (1 << channel)<<24 # look only at masked flag
        pick_list = self._data[:, COL.FLAG] & test_flag != 0
        return col_data[pick_list]

    def get_rej1_points(self, channel):
        """ get points marked as directly rejected by filter """
        if channel >= COL.CHANNELS:
            print('channel specification ',channel,' exceeds number of channel (',COL.CHANNELS,')')
            return None
        col_data = self._data[:, (COL.TIME, COL.CH1+channel)]
        test_flag = (1 << channel)<<8 # pick what is filtered
        pick_list1 = self._data[:, COL.FLAG] & test_flag != 0
        test_flag = (1 << channel)<<24 # but not masked
        pick_list2 = self._data[:, COL.FLAG] & test_flag == 0
        return col_data[np.logical_and(pick_list1, pick_list2)]

    def get_rej2_points(self, channel):
        """ get points rejected only due to problem with critical channel """
        if channel >= COL.CHANNELS:
            print('channel specification ',channel,' exceeds number of channel (',COL.CHANNELS,')')
            return None
        col_data = self._data[:, (COL.TIME, COL.CH1+channel)]
        test_flag = (1 << channel)<<16 # pick what is rejected by transfer
        pick_list1 = self._data[:, COL.FLAG] & test_flag != 0
        test_flag = (1 << channel)<<8 | (1 << channel)<<24 # and not directly rejected or masked
        pick_list2 = self._data[:, COL.FLAG] & test_flag == 0
        return col_data[np.logical_and(pick_list1, pick_list2)]

    ########################################################################################
    def evaluate_data(self):
        """ evaluate filtered data """
        new_adev_obj = ADevData(COL.CHANNELS) # make new object to store ADev data
        reference_values = self._channel_table.adev_ref()

        for ch_index in range(COL.CHANNELS):
            data = self.get_good_points([ch_index])
            times = data[:,0]
            values = data[:,1]
            meanval = np.mean(values)
            #print("mean of channel ",ch_index+1," is ",meanval)
            self._channel_table.set_mean(ch_index, meanval)
            # TODO: extract rate from data, adjust for deadtime?
            rate = 1 # one datapoint per second
            (taus_used, adev, adeverror, adev_n) = allantools.oadev(
                values, data_type='freq', rate=rate, taus='decade'
                )
            # scale to fractional values according to table settings
            adev /= reference_values[ch_index]
            adeverror /= reference_values[ch_index]
            #print('channel index: ', index)
            #print('taus: ',taus_used)
            #print('adev: ',adev)
            #print("adeverror: ",adeverror)
            del adev_n
            new_adev_obj.add_data(ch_index, taus_used, adev, adeverror)
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

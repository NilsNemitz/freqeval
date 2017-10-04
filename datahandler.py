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
from datetime import datetime, timezone
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
        self._data = None
        self._cache = {}
        self._empty = True
        self.ch_adev = None
        self._tday = 0
        self._tmin = 0
        self._baselines = [0] * 4
        self.filename = None
        self.ranges = [] # holds full data range for each channel later
        self._eval_data = [[]] # list of one empty list, will hold evaluation data later

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
        self._cache = {} # clear cache
        del data_frame

        # print(self.data[:, COL.STAT])

        # append a new column of uint16 zeros to indicate status flags
        # "status flag" format (True values indicate rejected data)
        # bits  0 -  7: overall channel rejection flags, used in final selection
        # bits  8 - 15: individual channel filter rejection flags
        # bits 16 - 23: global filter rejection flags (transfered from CEO and frep)
        # bits 24 - 31: mask indication, used to display manually rejected data
        npstatval = np.zeros(self._data.shape[0], dtype=np.uint32, order='C')
        
        # assume succesful load, updata data and filename
        self._data = np.c_[self._data, npstatval]
        self.filename = filename
        
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

        all_time_steps = self._data[1:-1, COL.TIME] - self._data[0:-2, COL.TIME]
        self._logic.adev_table.generate_taus(np.median(all_time_steps))

        baselines = self._logic.channel_table.parameters['base']
        print("baselines: ", baselines)

        self.ranges = []
        # TODO: can this be handled in a way that allows changing it for already loaded data?
        for index in range(COL.CHANNELS):
            self._data[:, COL.COLS[index]] -= baselines[index]
            if len(self._data) < 1:
                this_range = {
                    'y_min' : -1, 'y_max' : 1, 't_min' : 0, 't_max' : 1
                    }
            else:
                this_range = {}
                this_range['y_min'] = self._data[:, COL.COLS[index]].min()
                this_range['y_max'] = self._data[:, COL.COLS[index]].max()
                this_range['t_min'] = self._data[0, COL.TIME]
                this_range['t_max'] = self._data[-1, COL.TIME]
            self.ranges.append(this_range)

        return len(self._data)

    ########################################################################################
    def filter_data(self, overhangs, threshold):
        """ reset data filters (except mask) and re-apply """
        bitmask = 0xFF000000

        for row in self._data:
            # clear everything except manual mask bits, update overall flags
            row[COL.FLAG] &= bitmask
            row[COL.FLAG] |= row[COL.FLAG] >> 24
        
        tolerances = self._logic.channel_table.parameters['tole']
        # print("tolerances: ", tolerances)
        is_critical = self._logic.channel_table.parameters['filt']
        # print("apply filters: ", filters)
        self.filter_unlocked(tolerances, is_critical, overhangs)
        self.filter_outliers(threshold, is_critical, overhangs)
        self.filter_gather_results()
        self._cache = {} # clear cache

    ########################################################################################
    def load_maskfile(self, maskfile):
        """load data from a frequency csv file"""
        col_names = ['chan','day', 'start', 'end']
        try:
            maskdata = pandas.read_csv(
                maskfile,
                header=0, names=col_names,
                engine='c',
                error_bad_lines=False,
                warn_bad_lines=True,
                parse_dates=['start','end'],
                #dtype = ['int32', 'int32', 'string', 'string']#,
                converters={"chan": lambda x: int(x, 2)}
            )
        except FileNotFoundError as error:
            print("no mask file found.")
            maskdata = []
        for index in range(len(maskdata)):
            # convert to timestamp relative to data reference point of previous UTC midnight
            start_timestring = maskdata.ix[index, 'start']
            try:
                start_datetime = datetime.strptime(start_timestring.strip(), "%H:%M:%S")
                start_datetime = start_datetime.replace( 
                    tzinfo=timezone.utc, day=1, month=1, year=1970
                )
                start_timestamp = start_datetime.timestamp()
                start_timestamp += maskdata.ix[index, 'day'] * 86400
            except ValueError as error:
                print("Conversion error: ",error)
                start_timestamp = 0
            maskdata.ix[index, 'start'] = start_timestamp
            # start_datetime2 = datetime.utcfromtimestamp(start_timestamp + self._tmin)
            
            end_timestring = maskdata.ix[index, 'end']
            try:
                end_datetime = datetime.strptime(end_timestring.strip(), "%H:%M:%S")
                end_datetime = end_datetime.replace( 
                    tzinfo=timezone.utc, day=1, month=1, year=1970
                    )
                end_timestamp = end_datetime.timestamp() + 0.05
                end_timestamp += maskdata.ix[index, 'day'] * 86400
            except ValueError as error:
                print("Conversion error: ",error)
                end_timestamp = 0            
            maskdata.ix[index, 'end'] = end_timestamp
            # end_datetime2 = datetime.utcfromtimestamp(end_timestamp + self._tmin)
            # diagnostic:
            # print('start: ' + str(start_timestring)
            #    + ' -> ' + str(start_timestamp) + ' -> ' + start_datetime2.isoformat()
            #    + '  /  end: ' + str(end_timestring)
            #    + ' -> ' + str(end_timestamp) + ' -> ' + end_datetime2.isoformat()
            #    )
        if(len(maskdata) == 0):
            # no data
            return(False, 0)        
        # force to numeric values, adding NaN when conversion is not possible.
        maskdata = maskdata.apply(pandas.to_numeric, errors='coerce')
        maskdata = maskdata.sort_values(by='start') # puts NaN values at the back
        maskdata = maskdata.reset_index(drop=True)
        #print(maskdata)
        mask_count = 0
        while(len(maskdata)>0):
            print("(Re)reading mask data: ", len(maskdata), " element(s) remain.")
            postponed_indices = []        
            length = len(self._data)
            data_index = 0
            mask_index = 0
            end_time = -1E20
            #print( maskdata)
            while(mask_index < len(maskdata)):
                # need to apply same correction as applied to main time stamps!
                prev_end_time = end_time
                start_time = maskdata['start'][mask_index] 
                if start_time < prev_end_time:
                    #print('mask blocks overlap, postponing:', mask_index)
                    postponed_indices.append(mask_index)
                    mask_index += 1
                    continue # try again with next block
                if math.isnan(maskdata['end'][mask_index]):
                    end_time = start_time + 0.05
                else:
                    end_time = maskdata['end'][mask_index] 
                    while end_time < start_time:
                        end_time += 86400 # allows spanning UTC 0:00
                if not math.isnan(maskdata['chan'][mask_index]):
                    channel_mask = 0xFF & maskdata['chan'][mask_index] # limit to 8-bit
                else:
                    channel_mask = 0x00
                #print('mask block ',mask_index, '(',channel_mask,')   from ', start_time, ' to ', end_time)
                while( # advance until data_index == start_time
                    data_index < length
                    and self._data[data_index, COL.TIME] < start_time
                    ):                
                    data_index += 1
                while( # advance until data_index > end_time
                    data_index < length
                    and self._data[data_index, COL.TIME] < end_time
                    ):
                    self._data[data_index, COL.FLAG] |= channel_mask 
                    self._data[data_index, COL.FLAG] |= (channel_mask << 24)
                    mask_count += 1
                    data_index += 1
                # done with this block, proceed to next one
                mask_index += 1

            maskdata = maskdata.iloc[postponed_indices,:].reset_index(drop=True)
            #print('maskdata: ',maskdata)
        # end of main while loop
        if mask_count > 0:
            self._cache = {} # clear cache
        print(
            'done, masked ', mask_count, 
            ' data points. Mask block remaining: ', len(maskdata)
            )
        return(True, mask_count)

    ########################################################################################
    def binary_search_data(self, time):
        """ fast search for an index corresponding to a given time """
        # fast exit if time is not in range
        first = 0
        if self._data[first, COL.TIME] > time:
            return(False, first)
        last = len(self._data)-1
        if self._data[last, COL.TIME] < time:
            return(False, last)
        
        found = False
        while first<=last and not found:
            midpoint = (first + last)//2
            if self._data[midpoint, COL.TIME] == time:
                found = True
            else:
                if time < self._data[midpoint, COL.TIME]:
                    last = midpoint-1
                else:
                    first = midpoint+1
        if found:
            # if exact time was found, data point is in midpoint.
            return(True, midpoint)
        else:
            # if not, first and last are now equal and together with midpoint bracket
            # the target time
            if abs(self._data[midpoint,COL.TIME]-time) < abs(self._data[first,COL.TIME]-time):
                return(True, midpoint)
            else:
                return(True, first)

    ########################################################################################
    def add_to_mask(self, tstart, tend, flags):
        """ mask additional points selected in interface """
        flags = (flags & 0xFF) # keep only eight bits
        flags = flags | (flags << 24) # simultaneously add mask and "not good" bits
        start_found, start_index = self.binary_search_data(tstart)
        end_found, end_index = self.binary_search_data(tend)
        print('start : ', start_found, '  ', start_index)
        print('end   : ', end_found, '  ', end_index)
        if (not start_found) and (not end_found):
            print(
                'Mask: selected time values (',
                tstart,' and ',tend,') are not in range --> no mask'
                )
            return 0
        if start_index > end_index:
            print('Mask: indices ', start_index, ' and ', end_index, 'out of order: --> no mask')
            return 0
        
        print('Mask: masking points from index ', start_index, ' to ', end_index)
        self._data[int(start_index):int(end_index+1), COL.FLAG] |= flags
        self._cache = {} # clear cache
        return end_index - start_index + 1
    
    ########################################################################################
    def save_maskfile(self, maskfile):
        """ save mask data """
        result = False
        message = 'undefined'
        try:
            with open(maskfile,'w', encoding="ascii") as file:
                outstring = 'channel ,day,  start  ,   end\n'
                file.write(outstring)
                flags = 0x00 # start with no mask set
                timestamp_a = 0
                timestamp_b = 0
                for row in self._data:
                    new_flags = (row[COL.FLAG] & 0xFF000000) >> 24
                    if new_flags == flags:
                        # still in the same block, push along timestamp_b
                        timestamp_b = row[COL.TIME]
                    else:                        
                        # new block:
                        # write out previous block: (flags) from (timestamp_a to timestamp_b)
                        if flags != 0x00:
                            #...but only if there *was* a mask
                            print('({:08b}) for {:f} --> {:f}'.format(
                                flags, timestamp_a, timestamp_b
                                ))
                            day = int(timestamp_a // 86400) # enable multi-day runs
                            start_date = datetime.utcfromtimestamp(timestamp_a + self._tmin)                    
                            end_date = datetime.utcfromtimestamp(timestamp_b + self._tmin)
                            outstring = '{:08b},{:3d},{:>9s},{:>9s}\n'.format(
                                flags, day, 
                                start_date.strftime("%H:%M:%S"),
                                end_date.strftime("%H:%M:%S")     
                                )
                            file.write(outstring)
                        # in any case, initialize new block
                        timestamp_a = timestamp_b = row[COL.TIME]
                        flags = new_flags
                    
                # at end of loop, we need to write out final block
                if flags != 0x00:
                    #...but only if there *was* a mask
                    print('({:08b}) for {:f} --> {:f}'.format(
                        flags, timestamp_a, timestamp_b
                        ))
                    day = timestamp_a // 86400 # enable multi-day runs
                    start_date = datetime.utcfromtimestamp(timestamp_a + self._tmin)                    
                    end_date = datetime.utcfromtimestamp(timestamp_b + self._tmin)
                    outstring = '{:08b},{:3d},{:>9s},{:>9s}\n'.format(
                        flag, day, 
                        start_date.strftime("%H:%M:%S"),
                        end_date.strftime("%H:%M:%S")     
                        )
                    file.write(outstring)
                result = True
                message = 'ok'
        except (FileNotFoundError, PermissionError, IOError) as error:
            errno, strerror = error.args 
            result = False
            message = 'Failed to open file '+maskfile+':\n'+strerror
        finally:
            file.close()
        return(result, message)

    ########################################################################################
    def save_report(self, repfile):
        """ generate and save report """
        print("dummy: save report file to "+repfile)
        return (False, "Not implemented.")
        
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
    def get_good_points_multiple(self, channel_list):
        """ get only points marked as good for all test_channels in list """
        channel_mask = 0
        col_list = [COL.TIME]
        for channel in channel_list:
            if channel >= COL.CHANNELS:
                print('channel specification ',channel,' exceeds number of channel (',COL.CHANNELS,')')
                return None
            channel_mask |= (1 << channel) # look only at gathered flag
            col_list.append(COL.CH1+channel)
        #print('list of columns: ',col_list)
#        col_data = self._data[:, (COL.TIME, COL.CH1+channel)]
        #print('repr of raw data: ', repr(self._data))
        if channel_mask in self._cache:
            print('using cached copy for bitmask {:8b}'.format(channel_mask))            
        else:
            col_data = self._data[:, col_list]
            #print('repr of col data: ', repr(col_data))
            pick_list = self._data[:, COL.FLAG] & channel_mask == 0
            self._cache[channel_mask] = col_data[pick_list]
            print('cached data for bitmask {:8b}'.format(channel_mask))
        #print('repr of sel data: ', repr(data))
        return self._cache[channel_mask]
            
    ########################################################################################
    def get_good_points(self, channel):
        """ get only points marked as good for all test_channels in list """
        if channel >= COL.CHANNELS:
            print('channel specification ',channel,' exceeds number of channel (',COL.CHANNELS,')')
            return None
        channel_mask = (1 << channel) # look only at gathered flag
        #col_list.append(COL.CH1+channel)
        if channel_mask in self._cache:
            print('using cached copy for bitmask {:8b}'.format(channel_mask))
        else:
            col_data = self._data[:, (COL.TIME, COL.CH1+channel)]
            pick_list = self._data[:, COL.FLAG] & channel_mask == 0
            self._cache[channel_mask] = col_data[pick_list]
            print('cached data for bitmask {:8b}')
        data = self._cache[channel_mask]
        #print('repr of sel data: ', repr(data))
        if len(data)<1:
            range_info = {
                'y_min' : -1, 'y_max' : 1, 't_min' : 0, 't_max' : 1
                }
        else:
            range_info = {}
            range_info['y_min'] = data[:, 1].min()
            range_info['y_max'] = data[:, 1].max()
            range_info['t_min'] = data[0, 0]
            range_info['t_max'] = data[-1, 0]
        return data, range_info

    ########################################################################################
    def get_evaluation_points(self, eval_index):
        """ get time series data for evaluation """
        if eval_index >= len(self._eval_data):
            print(
                'evaluation specification ', eval_index,
                ' exceeds number of evaluations (', len(self._eval_data),')'
                )
            return []
        return self._eval_data[eval_index]

    ########################################################################################
    def get_mskd_points(self, channel):
        if channel >= COL.CHANNELS:
            print('channel specification ',channel,' exceeds number of channel (',COL.CHANNELS,')')
            return None
        col_data = self._data[:, (COL.TIME, COL.CH1+channel)]
        test_flag = (1 << channel)<<24 # look only at masked flag
        pick_list = self._data[:, COL.FLAG] & test_flag != 0
        return col_data[pick_list]

    ########################################################################################
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

    ########################################################################################
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
    def get_tmin(self):
        """ access reference tmin value (UNIX timestamp) """
        return self._tmin

    ########################################################################################
    def evaluate_ch_data(self):
        """ evaluate filtered data """
        #new_adev_obj = ADevData(COL.CHANNELS) # make new object to store ADev data
        reference_values = self._logic.channel_table.parameters['aref']

        for ch_index in range(COL.CHANNELS):
            # TODO: This should not collect good data again, but use a buffered copy
            data, range_info = self.get_good_points(ch_index)
            del range_info
            times = data[:,0]
            values = data[:,1]
            meanval = np.mean(values)
            #print("mean of channel ",ch_index+1," is ",meanval)
            self._logic.channel_table.set_mean(ch_index, meanval)
            # prepare ADev data
            adev = self.calculate_adev(values, reference_values[ch_index])
            self._logic.adev_table.add_channel_adev(ch_index, adev)
            # print('adev results for channel ', ch_index, '\n', adev)

    ########################################################################################
    def evaluate_eval_data(self):
        """ evaluate filtered data """
        self._eval_data = []
        for cnt in range(self._logic.evaluation_table.count):
            params = self._logic.evaluation_table.parameters[cnt]
            ###########################################################################
            if params['type'] == 1: # absolute frequency mode
                # print('(evaluation ',cnt,') absolute frequency : ',params['name'])
                # absolute frequency in terms of maser reference is:
                # f = fCEO + "n_a" * frep + f_beat
                # f = fCEO(MEASURED) + "n_a"/"n_r" * frep(MEASURED) + f_beat(MEASURED) 
                # f = baseline + fCEO(DEVIATION) + "n_a"/"n_r" * frep(DEVIATION) + f_beat(DEVIATION)
                # negative channel indices indicate negative beat frequencies
                ch_ceo = params['ch_ceo']-1
                if ch_ceo < 0:
                    s_ceo = -1 # set negative sign
                else:
                    s_ceo = +1 # set positive sign
                ch_ceo = int(abs(ch_ceo))
                ch_rep = int(abs(params['ch_rep'])-1)  # repetition rate is always positive
                n_rep = params['n_rep'] # set f_rep harmonic
                n_a = abs(params['n_a']) # set line index
                ch_a = int(params['ch_a']-1)
                if ch_a < 0:
                    s_a = -1 # set negative sign
                else:
                    s_a = +1 # set positive sign
                ch_a = int(abs(ch_a))

                #print('calculating relative frequency as:')
                #outstring = '{:+2.0f}*(CH{:1.0f}) {:+2.0f}*(CH{:1.0f})/{:2.0f} {:+2.0f}*(CH{:1.0f})'.format(
                #    s_ceo, ch_ceo,
                #    n_a, ch_rep, n_rep,
                #    s_a, ch_a
                #)
                #print(outstring)
                data= self.get_good_points_multiple((ch_ceo, ch_rep, ch_a))
                row_vector = np.array([0, s_ceo, n_a/n_rep, s_a], dtype=np.float64) # relative frequency, see above
                multiplier = float(params['multiplier'])
                # print('multiplier: ',multiplier)
                row_vector *= multiplier  # correction for In frequency
                values = data.dot(row_vector)                
                times = data[:,0]
            ###########################################################################
            elif params['type'] == 2: # frequency ratio mode                
                #print('(evaluation ',cnt,') frequency ratio    : ',params['name'])
                # frequency ratio is relative to comb line ratio is:
                # R = r_ab + ( (fCEO + f_a) - r_ab ( fCEO + f_b ) ) / (n_b f_rep + fCEO + f_b)
                # R = r_ab + ( (fCEO + f_a) - r_ab ( fCEO + f_b ) ) / f_target_b
                #     with correction at 1E-6 relative to r_ab:
                #     can afford 1E-13 deviation of true Sr frequency from target for 1E-19 accuracy
                #     r_ab already contains multiplier.
                ch_ceo = params['ch_ceo']-1
                if ch_ceo < 0:
                    s_ceo = -1 # set negative sign
                else:
                    s_ceo = +1 # set positive sign
                ch_ceo = int(abs(ch_ceo))
                r_ab = params['r_ab'] # set line ratio
                ch_a = int(params['ch_a']-1)
                if ch_a < 0:
                    s_a = -1 # set negative sign
                else:
                    s_a = +1 # set positive sign
                ch_a = int(abs(ch_a))
                ch_b = int(params['ch_b']-1)
                if ch_b < 0:
                    s_b = -1 # set negative sign
                else:
                    s_b = +1 # set positive sign
                ch_b = int(abs(ch_b))
                # relative correction to ratio value
                row_vector = np.array([0, s_ceo - s_ceo*r_ab, s_a, -s_b*r_ab], dtype=np.float64) 
                # division by reference frequency is part of equation
                # multiplier covers In fourth-harmonic generation
                multiplier = float(params['multiplier'])
                ref_b = float(params['ref_b'])
                # print('multiplier: ',multiplier,'    reference (b): ', ref_b)
                row_vector *= multiplier/ref_b

                data= self.get_good_points_multiple((ch_ceo, ch_a, ch_b))
                values = data.dot(row_vector)                
                times = data[:,0]
            ###########################################################################
            else:
                times = []
                values = []
            # print('shape of ...times:', times.shape, ' ...values', values.shape )                
            rel_data = np.column_stack((times, values))                
            #print('shape of resulting relative data: ', rel_data.shape)
            #print('repr. of resulting relative data: ', repr(rel_data))
            self._eval_data.append(rel_data)
            self._logic.evaluation_table.set_means(
                cnt,
                np.mean(times),
                np.mean(values)
                )
            adev = self.calculate_adev(values, float(params['target']))
            self._logic.adev_table.add_evaluation_adev(cnt, adev)
        # end of evaluation enumeration

    ########################################################################################
    def calculate_adev(self, values, reference):                       
        """ calculate Allan deviation and confidence intervals """
        time_step = self._logic.adev_table.time_step 
        rate = 1/time_step
        tau_req = self._logic.adev_table.tau_values
        (tau_act, devs, errs, ns) = allantools.oadev(values, rate=rate, data_type='freq', taus=tau_req)
        devs_lower = np.zeros_like(devs)
        devs_upper = np.zeros_like(devs)
        for (index, tau) in enumerate(tau_act):
            # sanity check tau values:
            if abs(tau-tau_req[index]) > 0.0001:
                print('Tau value differs from expectation: ', tau,' != ',tau_req[index])
            dev = devs[index]
            # Greenhall's EDF (Equivalent Degrees of Freedom)
            edf = allantools.edf_greenhall(
                alpha=0, # assuming WFM noise  (alpha +2,...,-4   noise type)
                d=2,     # 1: first-difference variance, 2: allan variance, 3: hadamard variance
                m=tau/time_step, # tau/tau0 averaging factor
                N=len(values), # number of observations
                overlapping=True, # sets stride to tau?
                modified=False,
                verbose=False
                )
            # To get CIs, for 1-sigma confidence we set
            # ci = scipy.special.erf(1/math.sqrt(2)) = 0.68268949213708585
            (lo, hi) = allantools.confidence_interval( 
                dev=dev, ci=0.68268949213708585, edf=edf 
                )
            devs_lower[index] = dev-lo
            devs_upper[index] = dev+hi
        adev = { # assembly into dictionary
            'taus':tau_act,
            'devs':devs,
            'devs_lower':devs_lower,
            'devs_upper':devs_upper,
            'frac_devs':devs/reference,
            'frac_devs_lower':devs_lower/reference,
            'frac_devs_upper':devs_upper/reference,
            'log_taus':np.log10(tau_act),
            'log_devs':np.log10(devs/reference),
            'log_devs_lower':np.log10(devs_lower/reference),
            'log_devs_upper':np.log10(devs_upper/reference),
            'ref':reference
            }
        return adev

########################################################################################
if __name__ == '__main__':
    print("test")

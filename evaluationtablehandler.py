#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
backend for evaluation matrix table
Created on 2017/09/10
@author: Nils Nemitz
"""

# pylint: disable=locally-disabled, bare-except

import decimal as dec

from PyQt5 import ( # pylint: disable=locally-disabled, no-name-in-module
    QtCore
    )

from PyQt5.QtCore import Qt as QtC # pylint: disable=locally-disabled, no-name-in-module

# import numpy as np

#from freqevalconstants import Gr # color definitions


class EvaluationTableModel(QtCore.QAbstractTableModel): # pylint: disable=locally-disabled, no-member
    """ adjust handling of data in evaluation matrix/table """

    ROW_NUMBER = 17
    ROW_HEADER = (
        "",
        "main line: n_a",
        "ref. line: n_b",
        "rep. rate: n_r",
        "",
        "line ratio a/b",
        "baseline freq.",
        "relative",
        "",
        "result",
        "uncertainty",
        "",
        "target",
        "deviation",
        "fractional dev",
        "fractional unc",
        ""
        )

    def __init__(self, parent, logic):
        super().__init__(parent)
        self._logic = logic
        self._data = []

    def set_from_config(self, config):
        """ sets up table content from config file """
        num_evaluations = config['CONFIG'].getint('evaluations', 3)
        self._data = []
        clist = []
        for index in range(num_evaluations):
            section = 'EVALUATION{:d}'.format(index+1)
            new_dict = {}
            new_dict['name'] = config[section].get('name', section)
            col = config[section].get('color', '#999999')
            clist.append(col)
            new_dict['show'] = config[section].getboolean('show', False)
            evaltype = config[section].get('type', 'none')
            if evaltype.lower() == 'absolute':
                new_dict['type'] = 1
            elif evaltype.lower() == 'ratio':
                new_dict['type'] = 2
            else:
                new_dict['type'] = -1
                print("ET.set_from_config: Unknown type specification: ", evaltype)
            
            line_index = config[section].getint('main_comb_line', 1)
            new_dict['n_a'] = dec.Decimal(line_index)
            new_dict['ch_a'] = config[section].getint('main_beat_channel', 1)
            
            line_index = config[section].getint('ref_comb_line', 1)
            new_dict['n_b'] = dec.Decimal(line_index)
            new_dict['ch_b'] = config[section].getint('ref_beat_channel', 1)
            
            line_index = config[section].getint('rep_rate_line', 1)
            new_dict['n_r'] = dec.Decimal(line_index)
            new_dict['ch_r'] = config[section].getint('rep_rate_channel', 1)
            
            target = config[section].get('target', '123456789012345667890')
            targetval = dec.Decimal(target) # store as arbitrary precision
            new_dict['target'] = targetval

            # calculate derived quantities

            baselines = self._logic.channel_table.baselines()
            corrections = self._logic.channel_table.corrections()
            ch_ceo = self._logic.channel_ceo
            ch_rep = self._logic.channel_rep
            ch_beat = new_dict['ch_a']
            n_a = new_dict['n_a']
            n_b = new_dict['n_b']
            n_r = new_dict['n_r']
            target = new_dict['target']

            #  define baselines as full precision decimals:
            if ch_ceo > 0:
                base_ceo = dec.Decimal(int(+baselines[+ch_ceo-1]))
                corr_ceo = dec.Decimal(int(+corrections[+ch_ceo-1]))
            else: # negative channel number indicates negative beat
                base_ceo = dec.Decimal(int(-baselines[-ch_ceo-1]))
                corr_ceo = dec.Decimal(int(-corrections[-ch_ceo-1]))
            base_ceo += corr_ceo

            base_rep = dec.Decimal(int(baselines[ch_rep-1]))
            corr_rep = dec.Decimal(int(corrections[ch_rep-1]))
            base_rep += corr_rep
            
            if ch_beat > 0:
                base_beat = dec.Decimal(int(+baselines[+ch_beat-1]))
                corr_beat = dec.Decimal(int(+corrections[+ch_beat-1]))
            else: # negative channel number indicates negative beat
                base_beat = dec.Decimal(int(-baselines[-ch_beat-1]))
                corr_beat = dec.Decimal(int(-corrections[-ch_beat-1]))
            base_beat += corr_beat
                        
            relative = dec.Decimal(0) # gets filled in later

            if new_dict['type'] == 1: # absolute frequency mode
                r_ab = n_a/n_r
                base_freq = base_ceo + (n_a/n_r) * base_rep + base_beat
                result = base_freq + relative
                uncert = dec.Decimal(1)                
                deviation = result - target
                frac_dev = deviation / result
                frac_unc = uncert / result
            elif new_dict['type'] == 2: # frequency ratio mode
                r_ab = n_a/n_b
                base_freq = dec.Decimal(0)
                result = r_ab + relative
                uncert = dec.Decimal(1E-15)
                deviation = result - target
                frac_dev = deviation / result
                frac_unc = uncert / result
            else:
                r_ab = dec.Decimal('NaN')
                base_freq = dec.Decimal('NaN')
                result = dec.Decimal('NaN')
                uncert = dec.Decimal('NaN')
                deviation = result - target
                frac_dev = dec.Decimal('NaN')
                frac_unc = dec.Decimal('NaN')
            print(
                'f_ceo: ',repr(base_ceo),
                '   f_rep: ',repr(base_rep),
                '   f_freq: ',repr(base_freq),
                '   decimals precision: ',dec.getcontext().prec
                )
            
            new_dict['r_ab'] = r_ab
            new_dict['base_freq'] = base_freq            
            new_dict['relative'] = relative # gets filled in later
            new_dict['result'] = result # gets updated later
            new_dict['uncert'] = uncert # gets filled in later
            new_dict['deviation'] = deviation
            new_dict['frac_dev'] = frac_dev
            new_dict['frac_unc'] = frac_unc
            self._data.append(new_dict)
        self._logic.set_evaluation_color_list(clist)
        return num_evaluations

    def columnCount(self, parent): # pylint: disable=locally-disabled, invalid-name
        """ TableView: return number of columns """
        del parent
        return self._logic.num_evaluations

    def rowCount(self, parent): # pylint: disable=locally-disabled, invalid-name
        """ TableView: return number of rows """
        del parent
        return self.ROW_NUMBER

    def headerData(self, col, orientation, role): # pylint: disable=locally-disabled, invalid-name
        """ TableView: return header strings and alignment """
        if orientation == QtC.Vertical:
            if role == QtC.DisplayRole:
                return self.ROW_HEADER[col]
            if role == QtC.TextAlignmentRole:
                return QtC.AlignRight | QtC.AlignVCenter
        return None

    def flags(self, index):
        """ TableView: return cell flags """
        if not index.isValid():
            return None
        #col = index.column()
        return QtC.ItemIsEnabled

    def data(self, index, role): # pylint: disable=locally-disabled, too-many-branches
        """ TableView: return formatted data """
        if not index.isValid():
            return None
        col = index.column()
        row = index.row()

        if row == 0:
            if role == QtC.DisplayRole:
                string = self._data[col]['name']
                return string
            elif role == QtC.BackgroundColorRole:
                color = self._logic.evaluation_color_list[col]
                return color
            elif role == QtC.ForegroundRole:
                return self._logic.BLACK
            elif role == QtC.TextAlignmentRole:
                return QtC.AlignCenter
            return None
        
        if role == QtC.TextAlignmentRole:
            return QtC.AlignCenter | QtC.AlignRight
        elif role == QtC.BackgroundColorRole:
            if row == 4 or row == 8 or row == 11 or row == 16: 
                color = self._logic.evaluation_color_list[col]
                return color
                # return self._logic.GRAY
        elif role != QtC.DisplayRole:
            return None

        string = ''
        if row == 1:
            string = '{:8f}  [ch {:+2d}]'.format(
                self._data[col]['n_a'],
                int(self._data[col]['ch_a'])
            )
        elif row == 2:
            if self._data[col]['type'] == 2:
                # reference line only used for ratio
                string = '{:8f}  [ch {:+2d}]'.format(
                    self._data[col]['n_b'],
                    int(self._data[col]['ch_b'])
                )
        elif row == 3:
            string = '{:8f}  [ch {:+2d}]'.format(
                self._data[col]['n_r'],
                int(self._data[col]['ch_r'])
            )
        elif row == 5:
            value = self._data[col]['r_ab']
            if self._data[col]['type'] == 1: # absolute frequency mode
                string = '{:24,.4f}'.format(value)
            elif self._data[col]['type'] == 2: # frequency ratio mode
                string = '{:24.19f}'.format(value)
            else:
                 string = 'undefined'

        elif row == 6:
            value = self._data[col]['base_freq']
            if self._data[col]['type'] == 1: # absolute frequency mode
                string = '{:24,.4f}'.format(value)
            elif self._data[col]['type'] == 2: # frequency ratio mode
                string = ''
            else:
                 string = 'undefined'
                                
        elif row == 7:
            value = self._data[col]['relative']
            if self._data[col]['type'] == 1: # absolute frequency mode
                string = '{:24,.4f}'.format(value)
            elif self._data[col]['type'] == 2: # frequency ratio mode
                string = '{:24,.19f}'.format(value)
            else:
                 string = 'undefined'

        elif row == 9:
            value = self._data[col]['result']
            if self._data[col]['type'] == 1: # absolute frequency mode
                string = '{:24,.4f}'.format(value)
            elif self._data[col]['type'] == 2: # frequency ratio mode
                string = '{:24,.19f}'.format(value)
            else:
                 string = 'undefined'

        elif row == 10:
            value = self._data[col]['uncert']
            if self._data[col]['type'] == 1: # absolute frequency mode
                string = '{:24,.4f}'.format(value)
            elif self._data[col]['type'] == 2: # frequency ratio mode
                string = '{:24,.19f}'.format(value)
            else:
                 string = 'undefined'

        elif row == 12:
            value = self._data[col]['target']
            if self._data[col]['type'] == 1: # absolute frequency mode
                string = '{:24,.4f}'.format(value)
            elif self._data[col]['type'] == 2: # frequency ratio mode
                string = ''
            else:
                 string = 'undefined'

        elif row == 13:
            value = self._data[col]['deviation']
            if self._data[col]['type'] == 1: # absolute frequency mode
                string = '{:24,.4f}'.format(value)
            elif self._data[col]['type'] == 2: # frequency ratio mode
                string = ''
            else:
                 string = 'undefined'

        elif row == 14:
            value = self._data[col]['frac_dev']
            value = round(value, 19)
            if self._data[col]['type'] == 1: # absolute frequency mode
                #string = '{:24,.19f}'.format(value)
                string = '{:E}'.format(value)
            elif self._data[col]['type'] == 2: # frequency ratio mode
                string = ''
            else:
                 string = 'undefined'
            
        elif row == 15:
            value = self._data[col]['frac_unc']
            value = round(value, 19)
            string = '{:E}'.format(value)

        return string
        if role == QtC.CheckStateRole:
            return None

#    def names(self):
#        """ getter function for channel filter toggles """
#        return self._data['name']

#    def filter_state(self):
#        """ getter function for channel filter toggles """
#        return self._data['filt']

#    def set_mean(self, index, value):
#        """ setter function for mean value """
#        if index < 0 or index >= self.ROW_NUMBER:
#            return
#        self._data[index]['mean'] = value + self._data[index]['base']

#    def print_data(self):
#        """ debug print of table status """
#        print(self._data['mean'])

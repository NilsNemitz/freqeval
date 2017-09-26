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

    ROW_NUMBER = 19
    ROW_HEADER = (
        "",
        "main  n_a",
        "ref.  n_b",
        "rep.  n_r",
        "multipl. // CEO",
        "",
        "line ratio",
        "baseline freq.",
        "relative",
        "",
        "syst. cor.",
        "result",
        "stat. unc.",
        "syst. unc.",
        "",
        "target",
        "deviation",
        "fract. dev.",
        "fract. unc.",
        ""
        )

    def __init__(self, parent, logic):
        super().__init__(parent)
        self._logic = logic
        self.parameters = []

    def set_from_config(self, config):
        """ sets up table content from config file """
        ceo_channel = config['CONFIG'].getint('ceo_channel', 0)
        rep_channel = config['CONFIG'].getint('rep_channel', 0)
        rep_line_index = config['CONFIG'].getint('rep_line_index', 1)
        num_evaluations = config['CONFIG'].getint('evaluations', 3)
        self.parameters = []
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
            del evaltype

            line_index = config[section].getint('main_comb_line', 1)
            reference = config[section].get('main_reference', '12345678901234567890')
            sys_cor = config[section].get('main_sys_cor', '0.000')
            sys_unc = config[section].get('main_sys_unc', '0.000')
            new_dict['n_a'] = dec.Decimal(line_index)
            new_dict['ch_a'] = config[section].getint('main_beat_channel', 1)
            new_dict['ref_a'] = dec.Decimal(reference) # store as arbitrary precision
            new_dict['sys_cor_a'] = dec.Decimal(sys_cor)
            new_dict['sys_unc_a'] = dec.Decimal(sys_unc)

            line_index = config[section].getint('ref_comb_line', 1)
            reference = config[section].get('ref', '12345678901234567890')
            sys_cor = config[section].get('main_sys_cor', '0.000')
            sys_unc = config[section].get('main_sys_unc', '0.000')
            reference = config[section].get('ref_reference', '12345678901234567890')
            new_dict['n_b'] = dec.Decimal(line_index)
            new_dict['ch_b'] = config[section].getint('ref_beat_channel', 1)
            new_dict['sys_cor_b'] = dec.Decimal(sys_cor)
            new_dict['sys_unc_b'] = dec.Decimal(sys_unc)
            new_dict['ref_b'] = dec.Decimal(reference) # store as arbitrary precision

            #line_index = config[section].getint('rep_rate_line', 1)
            new_dict['ch_ceo'] = ceo_channel
            new_dict['ch_rep'] = rep_channel
            new_dict['n_rep'] = dec.Decimal(rep_line_index)

            del reference
            del sys_cor
            del sys_unc
            new_dict['show'] = config[section].getboolean('show', True)

            multiplier = config[section].get('multiplier', 1) # direct to Decimal
            new_dict['multiplier'] = dec.Decimal(multiplier)
            del multiplier

        ##################################
        # cut loop here
        #   del rep_line_index
        #   del ceo_channel
        #   del rep_channel
        ##################################

            # calculate derived quantities
            # TODO: inline dictionary values where appropriate
            baselines = self._logic.channel_table.baselines()
            corrections = self._logic.channel_table.corrections()
            #ch_ceo = self._logic.channel_ceo
            #ch_rep = self._logic.channel_rep
            ch_ceo = new_dict['ch_ceo']
            ch_rep = new_dict['ch_rep']
            ch_beat = new_dict['ch_a']
            n_a = new_dict['n_a']
            n_b = new_dict['n_b']
            n_rep = new_dict['n_rep']
            multiplier = new_dict['multiplier']
            ref_a = new_dict['ref_a']
            sys_cor_a = new_dict['sys_cor_a']
            sys_unc_a = new_dict['sys_unc_a']
            ref_b = new_dict['ref_b']
            sys_cor_b = new_dict['sys_cor_b']
            sys_unc_b = new_dict['sys_unc_b']

            #  define baselines as full precision decimals:
            if ch_ceo > 0:
                base_ceo = dec.Decimal(int(+baselines[abs(ch_ceo)-1]))
                corr_ceo = dec.Decimal(int(+corrections[abs(ch_ceo)-1]))
            else: # negative channel number indicates negative beat
                base_ceo = dec.Decimal(int(-baselines[abs(ch_ceo)-1]))
                corr_ceo = dec.Decimal(int(-corrections[abs(ch_ceo)-1]))
            base_ceo += corr_ceo
            del corr_ceo

            base_rep = dec.Decimal(int(baselines[ch_rep-1]))
            corr_rep = dec.Decimal(int(corrections[ch_rep-1]))
            base_rep += corr_rep
            del corr_rep

            if ch_beat > 0:
                base_beat = dec.Decimal(int(+baselines[abs(ch_beat)-1]))
                corr_beat = dec.Decimal(int(+corrections[abs(ch_beat)-1]))
            else: # negative channel number indicates negative beat
                base_beat = dec.Decimal(int(-baselines[abs(ch_beat)-1]))
                corr_beat = dec.Decimal(int(-corrections[abs(ch_beat)-1]))
            base_beat += corr_beat
            del corr_beat
            del baselines
            del corrections

            relative = dec.Decimal(0) # gets filled in later
            # TODO: should be NaN until filled

            if new_dict['type'] == 1: # absolute frequency mode
                r_ab = n_a/n_rep
                base_freq = base_ceo + (n_a/n_rep) * base_rep + base_beat
                #print("base_freq value: ", base_freq)
                #print("base_freq object: ", repr(base_freq))
                #print("multiplier value: ", multiplier)
                #print("multiplier object: ", repr(multiplier))
                base_freq = multiplier * base_freq # scaling for Indium clock
                sys_cor = sys_cor_a # direct correction for systematic effects
                sys_unc = sys_unc_a # direct correction for systematic effects
                result = base_freq + relative + sys_cor
                stat_unc = dec.Decimal(1)
                target = ref_a
                deviation = result - target
                frac_dev = deviation / result
                frac_unc = stat_unc / result
            elif new_dict['type'] == 2: # frequency ratio mode
                r_ab = n_a/n_b
                r_ab *= multiplier
                base_freq = dec.Decimal(0)
                sys_cor = dec.Decimal('NaN')
                sys_unc = dec.Decimal('NaN')
                result = r_ab + relative
                stat_unc = dec.Decimal(1E-15)
                target = ref_a / ref_b
                deviation = result - target
                frac_dev = deviation / result
                frac_unc = stat_unc / result
            else:
                r_ab = dec.Decimal('NaN')
                base_freq = dec.Decimal('NaN')
                result = dec.Decimal('NaN')
                stat_unc = dec.Decimal('NaN')
                deviation = dec.Decimal('NaN')
                frac_dev = dec.Decimal('NaN')
                frac_unc = dec.Decimal('NaN')
                sys_corr = dec.Decimal('NaN')
                sys_unc = dec.Decimal('NaN')
            print(
                'f_ceo: ', repr(base_ceo),
                '   f_rep: ', repr(base_rep),
                '   f_freq: ', repr(base_freq),
                '   decimals precision: ', dec.getcontext().prec
                )
            # calculation (particularly of ratio value) uses reference value
            # in places where full accuracy is not required.
            # for ratio "relative" number, the correction term is of order 1E-7
            # (40 MHz AOM shifts over 400 THz Sr optical frequency)
            # a relative error of 1E-12 is therefore acceptable to achieve 1E-19
            # accuracy. If.
            if frac_dev > 1E-12:
                new_dict['deviation_warning'] = True
                num_string = '{:3.1E}'.format(frac_dev)
                text = (
                    'The current evaluation for ' + new_dict['name']
                    + ' deviates by ' + num_string
                    + ' from reference value.\nResults will be inaccurate.'
                )
                self._logic.warning('Deviation from reference', text)
            new_dict['r_ab'] = r_ab
            new_dict['base_freq'] = base_freq
            new_dict['relative'] = relative # gets filled in later
            new_dict['result'] = result # gets updated later
            new_dict['uncert'] = stat_unc # gets filled in later
            new_dict['sys_cor'] = sys_cor
            new_dict['sys_unc'] = sys_unc
            new_dict['target'] = target
            new_dict['deviation'] = deviation
            new_dict['frac_dev'] = frac_dev
            new_dict['frac_unc'] = frac_unc
            self.parameters.append(new_dict)
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

        # number formatting for absolute frequency and ratio results
        style_absolute = '{:24,.4f}'
        style_ratio = '{:24,.19f}'
        if self.parameters[col]['type'] == 1: # absolute frequency mode
            style = style_absolute
        elif self.parameters[col]['type'] == 2: # frequency ratio mode
            style = style_ratio
        else:
            style = 'undefined'

        if row == 0:
            if role == QtC.DisplayRole:
                string = self.parameters[col]['name']
                return string
            elif role == QtC.BackgroundColorRole:
                color = self._logic.evaluation_color_list[col]
                return color
            elif role == QtC.ForegroundRole:
                return self._logic.BLACK
            elif role == QtC.TextAlignmentRole:
                return QtC.AlignCenter
            elif role == QtC.CheckStateRole:
                if self.parameters[col]['show']:
                    return QtC.Checked
                else:
                    return QtC.Unchecked
            return None

        if role == QtC.TextAlignmentRole:
            return QtC.AlignCenter | QtC.AlignRight
        elif role == QtC.BackgroundColorRole:
            divider_rows = [5, 9, 14, 19]
            if row in divider_rows:
                color = self._logic.evaluation_color_list[col]
                return color                
        elif role != QtC.DisplayRole:
            return None

        string = ''
        if row == 1:
            string = '{:11,.0f}     [ch {:+2d}]'.format(
                self.parameters[col]['n_a'],
                int(self.parameters[col]['ch_a'])
            )
        elif row == 2:
            if self.parameters[col]['type'] == 2:
                # reference line only used for ratio
                string = '{:11,.0f}     [ch {:+2d}]'.format(
                    self.parameters[col]['n_b'],
                    int(self.parameters[col]['ch_b'])
                )
        elif row == 3:
            string = '{:11,.0f}     [ch {:+2d}]'.format(
                self.parameters[col]['n_rep'],
                int(self.parameters[col]['ch_rep'])
            )
        elif row == 4:
            string = '{:11,.0f} // [ch {:+2d}]'.format(
                self.parameters[col]['multiplier'],
                int(self.parameters[col]['ch_ceo'])
            )
        elif row == 6:
            value = self.parameters[col]['r_ab']
            string = style.format(value)
            #if self.parameters[col]['type'] == 1: # absolute frequency mode
            #    string = '{:24,.4f}'.format(value)
            #elif self.parameters[col]['type'] == 2: # frequency ratio mode
            #    string = '{:24.19f}'.format(value)
            #else:
            #    string = 'undefined'

        elif row == 7:
            value = self.parameters[col]['base_freq']
            string = style.format(value)
            if self.parameters[col]['type'] == 1: # absolute frequency mode
                string = style.format(value)
            else:
                string = ''
            #    string = '{:24,.4f}'.format(value)
            #elif self.parameters[col]['type'] == 2: # frequency ratio mode
            #    string = ''
            #else:
            #    string = 'undefined'

        elif row == 8:
            value = self.parameters[col]['relative']
            string = style.format(value)
            #if self.parameters[col]['type'] == 1: # absolute frequency mode
            #    string = '{:24,.4f}'.format(value)
            #elif self.parameters[col]['type'] == 2: # frequency ratio mode
            #    string = '{:24,.19f}'.format(value)
            #else:
            #    string = 'undefined'

        elif row == 10:
            value = self.parameters[col]['sys_cor']
            string = style.format(value)
            #if self.parameters[col]['type'] == 1: # absolute frequency mode
            #    string = '{:24,.4f}'.format(value)
            #elif self.parameters[col]['type'] == 2: # frequency ratio mode
            #    string = '{:24,.19f}'.format(value)
            #else:
            #    string = 'undefined'

        elif row == 11:
            value = self.parameters[col]['result']
            string = style.format(value)
            #if self.parameters[col]['type'] == 1: # absolute frequency mode
            #    string = '{:24,.4f}'.format(value)
            #elif self.parameters[col]['type'] == 2: # frequency ratio mode
            #    string = '{:24,.19f}'.format(value)
            #else:
            #    string = 'undefined'

        elif row == 12:
            value = self.parameters[col]['uncert']
            string = style.format(value)
            #if self.parameters[col]['type'] == 1: # absolute frequency mode
            #    string = '{:24,.4f}'.format(value)
            #elif self.parameters[col]['type'] == 2: # frequency ratio mode
            #    string = '{:24,.19f}'.format(value)
            #else:
            #    string = 'undefined'

        elif row == 13:
            value = self.parameters[col]['sys_unc']
            string = style.format(value)
            #if self.parameters[col]['type'] == 1: # absolute frequency mode
            #    string = '{:24,.4f}'.format(value)
            #elif self.parameters[col]['type'] == 2: # frequency ratio mode
            #    string = '{:24,.19f}'.format(value)
            #else:
            #    string = 'undefined'

        elif row == 15:
            value = self.parameters[col]['target']
            string = style.format(value)
            #if self.parameters[col]['type'] == 1: # absolute frequency mode
            #    string = '{:24,.4f}'.format(value)
            #elif self.parameters[col]['type'] == 2: # frequency ratio mode
            #    string = '{:24,.19f}'.format(value)
            #    #string = ''
            #else:
            #    string = 'undefined'

        elif row == 16:
            value = self.parameters[col]['deviation']
            string = style.format(value)
            #if self.parameters[col]['type'] == 1: # absolute frequency mode
            #    string = '{:24,.4f}'.format(value)
            #elif self.parameters[col]['type'] == 2: # frequency ratio mode
            #    string = ''
            #else:
            #    string = 'undefined'

        elif row == 17:
            value = self.parameters[col]['frac_dev']
            value = round(value, 19)
            string = '{:E}'.format(value)
            #if self.parameters[col]['type'] == 1: # absolute frequency mode
            #    #string = '{:24,.19f}'.format(value)
            #    string = '{:E}'.format(value)
            #elif self.parameters[col]['type'] == 2: # frequency ratio mode
            #    string = ''
            #else:
            #    string = 'undefined'

        elif row == 18:
            value = self.parameters[col]['frac_unc']
            value = round(value, 19)
            string = '{:E}'.format(value)

        return string
    # TODO: implement plotting selection box
        if role == QtC.CheckStateRole:
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

#    def names(self):
#        """ getter function for channel filter toggles """
#        return self.parameters['name']

#    def filter_state(self):
#        """ getter function for channel filter toggles """
#        return self.parameters['filt']

#    def set_mean(self, index, value):
#        """ setter function for mean value """
#        if index < 0 or index >= self.ROW_NUMBER:
#            return
#        self.parameters[index]['mean'] = value + self.parameters[index]['base']

#    def print_data(self):
#        """ debug print of table status """
#        print(self.parameters['mean'])

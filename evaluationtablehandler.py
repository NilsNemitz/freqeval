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

#import numpy as np
from freqevalconstants import Gr # color definitions

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
        "baseline",
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

    #######################################################################
    def __init__(self, parent, logic):
        super().__init__(parent)
        self._logic = logic
        self.count = 0 # number of known evaluations
        self.parameters = []

    #######################################################################
    def set_from_config(self, config):
        """ sets up table content from config file """
        ceo_channel = config['CONFIG'].getint('ceo_channel', 0)
        rep_channel = config['CONFIG'].getint('rep_channel', 0)
        rep_line_index = config['CONFIG'].getint('rep_line_index', 1)
        self.count = config['CONFIG'].getint('evaluations', 3)
        self.parameters = []
        for index in range(self.count):
            section = 'EVALUATION{:d}'.format(index+1)
            new_dict = {}
            new_dict['name'] = config[section].get('name', section)
            new_dict['color'] = self._logic.make_color(
                config[section].get('color', '#999999')
                )
            new_dict['show'] = config[section].getboolean('show', False)
            new_dict['ch_ceo'] = ceo_channel
            new_dict['ch_rep'] = rep_channel
            new_dict['n_rep'] = dec.Decimal(rep_line_index)

            evaltype = config[section].get('type', 'none')
            if evaltype.lower() == 'absolute':
                new_dict['type'] = 1
            elif evaltype.lower() == 'ratio':
                new_dict['type'] = 2
            else:
                new_dict['type'] = -1
                print("ET.set_from_config: Unknown type specification: ", evaltype)
            del evaltype
            new_dict['n_a'] = dec.Decimal( # store as arbitrary precision
                config[section].getint('main_comb_line', 1)
                )
            new_dict['ch_a'] = ( # store as integer
                config[section].getint('main_beat_channel', 1)
                )
            new_dict['ref_a'] = dec.Decimal( # store as arbitrary precision
                config[section].get('main_reference', '12345678901234567890')
                )
            new_dict['ref_a_unc'] = dec.Decimal( # store as arbitrary precision
                config[section].get('main_reference_unc', '1')
                )
            new_dict['sys_cor_a'] = dec.Decimal( # store as arbitrary precision
                config[section].get('main_sys_cor', '0.000')
                )
            new_dict['sys_unc_a'] = dec.Decimal( # store as arbitrary precision
                config[section].get('main_sys_unc', '0.000')
                )
            new_dict['n_b'] = dec.Decimal( # store as arbitrary precision
                config[section].getint('ref_comb_line', 1)
                )
            new_dict['ch_b'] = ( # store as integer
                config[section].getint('ref_beat_channel', 1)
                )
            new_dict['ref_b'] = dec.Decimal( # store as arbitrary precision
                config[section].get('ref_reference', '12345678901234567890')
                )
            new_dict['sys_cor_b'] = dec.Decimal( # store as arbitrary precision
                config[section].get('main_sys_cor', '0.000')
                )
            new_dict['sys_unc_b'] = dec.Decimal( # store as arbitrary precision
                config[section].get('main_sys_unc', '0.000')
                )
            new_dict['multiplier'] = dec.Decimal( # store as arbitrary precision
                config[section].get('multiplier', 1)
                )
            new_dict['mean_relative'] = dec.Decimal('NaN')
            new_dict['mean_time'] = dec.Decimal('NaN')
            new_dict['stat_unc'] = dec.Decimal('NaN')
            self.parameters.append(new_dict)
        ### done initializing parameter dictionary ###############################

    #######################################################################
    def set_means(self, index, mean_time, mean_value):
        """ called by data handler to set mean time and evaluation value """
        self.parameters[index]['mean_time'] = dec.Decimal(mean_time)
        self.parameters[index]['mean_relative'] = dec.Decimal(mean_value)
#        print(
#            'mean values ',self.parameters[index]['mean_relative'],
#            ' @ ',self.parameters[index]['mean_time']
#            )

    #######################################################################
    def update(self):
        """ update calculation results for values now in parameters """
        print("updating evaluation table")
        baselines = self._logic.channel_table.parameters['base']
        corrections = self._logic.channel_table.parameters['corr']
        for index in range(self.count):
            par = self.parameters[index] # parameter dictionary for this evaluation
            # calculate derived quantities
            ch_ceo = par['ch_ceo']
            if ch_ceo > 0:
                base_ceo = dec.Decimal(int(+baselines[abs(ch_ceo)-1]))
                corr_ceo = dec.Decimal(int(+corrections[abs(ch_ceo)-1]))
            else: # negative channel number indicates negative beat
                base_ceo = dec.Decimal(int(-baselines[abs(ch_ceo)-1]))
                corr_ceo = dec.Decimal(int(-corrections[abs(ch_ceo)-1]))
            base_ceo += corr_ceo
            
            ch_rep = par['ch_rep']            
            base_rep = dec.Decimal(int(baselines[ch_rep-1]))
            corr_rep = dec.Decimal(int(corrections[ch_rep-1]))
            base_rep += corr_rep
            
            ch_beat = par['ch_a']
            if ch_beat > 0:
                base_beat = dec.Decimal(int(+baselines[abs(ch_beat)-1]))
                corr_beat = dec.Decimal(int(+corrections[abs(ch_beat)-1]))
            else: # negative channel number indicates negative beat
                base_beat = dec.Decimal(int(-baselines[abs(ch_beat)-1]))
                corr_beat = dec.Decimal(int(-corrections[abs(ch_beat)-1]))
            base_beat += corr_beat
            del corr_ceo, corr_rep, corr_beat
            
            relative = par['mean_relative'] # extracted from time series data
            stat_unc = par['stat_unc'] # extracted from Allan deviation
            n_a = par['n_a']
            n_b = par['n_b']
            n_rep = par['n_rep']
            multiplier = par['multiplier']
            ref_a = par['ref_a']
            sys_cor_a = par['sys_cor_a']
            sys_unc_a = par['sys_unc_a']
            ref_b = par['ref_b']
            sys_cor_b = par['sys_cor_b']
            sys_unc_b = par['sys_unc_b']
            
            if par['type'] == 1: # absolute frequency mode
                r_ab = n_a/n_rep
                result_baseline = base_ceo + (n_a/n_rep) * base_rep + base_beat
                result_baseline = multiplier * result_baseline # scaling for Indium clock
                sys_cor = sys_cor_a # direct correction for systematic effects
                sys_unc = sys_unc_a # direct correction for systematic effects
                target = ref_a
            elif par['type'] == 2: # frequency ratio mode
                r_ab = n_a/n_b # r_ab does not include multiplier 
                result_baseline = r_ab * multiplier # baseline is line ratio * multiplier
                target = ref_a / ref_b
                rel_cor_a = sys_cor_a / ref_a
                rel_cor_b = sys_cor_b / ref_b
                sys_cor = (rel_cor_a - rel_cor_b) * target                
                sys_var = (sys_unc_a/ref_a)**2 + (sys_unc_b/ref_b)**2                
                sys_unc = sys_var.sqrt()                
            else:
                r_ab = dec.Decimal('NaN')
                result_baseline = dec.Decimal('NaN')
                frac_dev = dec.Decimal('NaN')
                frac_unc = dec.Decimal('NaN')
                sys_cor = dec.Decimal('NaN')
                sys_unc = dec.Decimal('NaN')
            
            result = result_baseline + relative + sys_cor
            deviation = result - target
            frac_dev = deviation / result

            tot_var = sys_unc**2 + stat_unc**2
            frac_unc = tot_var.sqrt() / result
            frac_dev = deviation / result
            frac_unc = stat_unc / result
            #print(
            #    'f_ceo: ', repr(base_ceo),
            #    '   f_rep: ', repr(base_rep),
            #    '   f_freq: ', repr(baseline),
            #    '   decimals precision: ', dec.getcontext().prec
            #    )
            # calculation (particularly of ratio value) uses reference value
            # in places where full accuracy is not required.
            # for ratio "relative" number, the correction term is of order 1E-7
            # (40 MHz AOM shifts over 400 THz Sr optical frequency)
            # a relative error of 1E-12 is therefore acceptable to achieve 1E-19
            # accuracy.
            if not relative.is_nan() and abs(relative/target) > 1E-7:
                par['deviation_warning'] = True
                num_string = '{:3.1E}'.format(target * dec.Decimal(1E-7))
                text = (
                    'The relative correction for ' + par['name']
                    + ' exceeds ' + num_string
                    + ' (1E-7). Results will be inaccurate.'
                )
                self._logic.warning('Deviation from reference', text)
                par['dev_warn'] = True
            else:
                par['dev_warn'] = False
            par['r_ab'] = r_ab
            par['baseline'] = result_baseline
            par['result'] = result
            par['uncert'] = stat_unc
            par['sys_cor'] = sys_cor
            par['sys_unc'] = sys_unc
            par['target'] = target
            par['deviation'] = deviation
            par['frac_dev'] = frac_dev
            par['frac_unc'] = frac_unc
        self.update_view()


    #######################################################################
    def columnCount(self, parent): # pylint: disable=locally-disabled, invalid-name
        """ TableView: return number of columns """
        del parent
        return self.count

    #######################################################################
    def rowCount(self, parent): # pylint: disable=locally-disabled, invalid-name
        """ TableView: return number of rows """
        del parent
        return self.ROW_NUMBER

    #######################################################################
    def headerData(self, col, orientation, role): # pylint: disable=locally-disabled, invalid-name
        """ TableView: return header strings and alignment """
        if orientation == QtC.Vertical:
            if role == QtC.DisplayRole:
                return self.ROW_HEADER[col]
            if role == QtC.TextAlignmentRole:
                return QtC.AlignRight | QtC.AlignVCenter
        return None

    #######################################################################
    def flags(self, index):
        """ TableView: return cell flags """
        if not index.isValid():
            return None
        #col = index.column()
        return QtC.ItemIsEnabled

    #######################################################################
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
                color = self.parameters[col]['color']
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
                color = self.parameters[col]['color']
                return color
            elif row == 8: # deviation warning
                if self.parameters[col]['dev_warn']:
                    return  Gr.DK_RED
                else:
                    return None
            elif row == 11: # highlight main result
                return  Gr.BLACK
            return None

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
        elif row == 7:
            value = self.parameters[col]['baseline']
            string = style.format(value)            
        elif row == 8:
            value = self.parameters[col]['mean_relative']
            string = style.format(value)
        elif row == 10:
            value = self.parameters[col]['sys_cor']
            string = style.format(value)
        elif row == 11:
            value = self.parameters[col]['result']
            string = style.format(value)
        elif row == 12:
            value = self.parameters[col]['uncert']
            string = style.format(value)
        elif row == 13:
            value = self.parameters[col]['sys_unc']
            string = style.format(value)
        elif row == 15:
            value = self.parameters[col]['target']
            string = style.format(value)
        elif row == 16:
            value = self.parameters[col]['deviation']
            string = style.format(value)
        elif row == 17:
            value = self.parameters[col]['frac_dev']
            value = round(value, 19)
            string = '{:E}'.format(value)
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
        self.dataChanged.emit(index_tl, index_br, [QtC.DisplayRole])

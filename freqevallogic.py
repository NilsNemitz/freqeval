#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Main logic code for frequency evaluation program
Created on 2017/09/04
@author: Nils Nemitz
"""

# py#lint: disable=locally-disabled, redefined-variable-type
# pylint: disable=locally-disabled, too-many-instance-attributes

import os.path
import configparser
import pyqtgraph_core as pg

from PyQt5 import Qt
from PyQt5.QtCore import Qt as QtC # pylint: disable=locally-disabled, no-name-in-module
from PyQt5.QtGui import QColor # pylint: disable=locally-disabled, no-name-in-module
from PyQt5.QtGui import QPen # pylint: disable=locally-disabled, no-name-in-module
# import pandas
import numpy as np
# import math

from freqevalconstants import Gr # color definitions
from datahandler import DataHandler, COL
from selectiontablehandler import SelectionTableModel
from channeltablehandler import ChannelTableModel
from adevtablehandler import ADevTableModel
from evaluationtablehandler import EvaluationTableModel

class SelectedPoints(object):
    """ stores two selected points and their time values for mask selection """
    def __init__(self):
        self.point_a = None
        self.color_a = None
        self.point_b = None
        self.color_b = None

# replaced by dictionary
#class PlotInformation(object):
#    """ stores reference to individual plots and their min/max values """
#    def __init__(self, reference):
#        self.ref = reference
#        # These will hold range information dictionary later
#        self.good = None 
#        self.full = None

class FreqEvalLogic(object):
    """program logic class for frequency evaluation program"""

    BLACK = QColor('Black')
    GRAY = QColor('DarkGray')

    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.gui.set_status("Initializing backend")
        self._ch_plots = []
        self._eval_plots = []
        self._data_obj = None
        self._points = SelectedPoints() # initialize point selection storage
        self.parameters = {
            'overhangs':[1, 10], # points marked bad before/after "out-of-band" point
            'threshold':10 # x-sigma threshold for outlier detection
        }
        self.config = configparser.ConfigParser()

#        self.eval_config['CONFIG'] = {
#            'channels':str(self.num_channels),
#            'outlier_threshold':str(self.threshold),
#            'evaluations':str(self.num_evaluations),
#            'ceo_channel':str(self.channel_ceo),
#            'rep_channel':str(self.channel_rep),
#            'rep_line_index':str(self.channel_rep)
#        }
#        for index in range(self.num_channels):
#            section = 'CHANNEL{:d}'.format(index+1)
#            #print("section name: "+section)
#            if not section in self.eval_config:
#                self.eval_config[section] = {}
#            string = 'ch {:d}'.format(index+1)
#            self.eval_config[section]['name'] = string
#            self.eval_config[section]['color'] = self.channel_color_list[index].name()
#            self.eval_config[section]['baseline'] = '0'
#            self.eval_config[section]['tolerance'] = '1000'
#            self.eval_config[section]['filter'] = 'yes'
#            self.eval_config[section]['correction'] = '0'
#            self.eval_config[section]['adev_reference'] = '1'

#        for index in range(self.num_evaluations):
#            section = 'EVALUATION{:d}'.format(index+1)
#            if not section in self.eval_config:
#                self.eval_config[section] = {}
#            string = 'eval {:d}'.format(index+1)
#            self.eval_config[section]['name'] = string
#            index_w_offset = index+self.num_channels
#            self.eval_config[section]['color'] = self.channel_color_list[index_w_offset].name()
#            self.eval_config[section]['show'] = 'yes'
#            self.eval_config[section]['type'] = 'absolute'
#            self.eval_config[section]['multiplier'] = '1'
#            self.eval_config[section]['main_comb_line'] = '1234567'
#            self.eval_config[section]['main_beat_channel'] = '3'
#            self.eval_config[section]['main_reference'] = '123123123123123.1234'
#            self.eval_config[section]['main_sys_cor'] = '0.200'
#            self.eval_config[section]['main_sys_unc'] = '0.100'
#            self.eval_config[section]['ref_comb_line'] = '0'
#            self.eval_config[section]['ref_beat_channel'] = '0'
#            self.eval_config[section]['ref_reference'] = '123123123123123.1234'
#            self.eval_config[section]['ref_sys_cor'] = '0.400'
#            self.eval_config[section]['ref_sys_unc'] = '0.300'

        print("reading default config file")
        self.config.read('default.cfg')

#        self.channel_ceo = self.eval_config['CONFIG'].getint('ceo_channel', 1)
#        self.channel_rep = self.eval_config['CONFIG'].getint('rep_channel', 1)
#        self.outlier_threshold = self.eval_config['CONFIG'].getfloat('outlier_threshold', 2)

 #       print("CEO / rep channels: ", self.channel_ceo, " / ", self.channel_rep)

        # logic class tracks table models and makes them available as needed
        self.selection_table = SelectionTableModel(None, self)
        self.channel_table = ChannelTableModel(None, self)
        self.channel_table.set_from_config()
        print("now ", self.channel_table.count, " channels known.")

        self.evaluation_table = EvaluationTableModel(None, self)
        self.evaluation_table.set_from_config(self.config)
        print("now ", self.evaluation_table.count, " evaluations known.")
        self.evaluation_table.update()

        self.adev_table = ADevTableModel(None, self)

        self.gui.set_status("Writing back to configuration file")
        with open('default.cfg', 'w') as configfile:
            self.config.write(configfile)

        # initialize graph references, to be populated after logic start
        self._g1 = self._g2 = None
        # self._pa1 = self._pa2 = self._pa3 = self._pa4 = None

    def init_graphs(self):
        """ initialize graphs after GUI has been initialized """
        self.gui.set_status("Initializing graphs")
        self._g1 = self.gui.graph1_layout
        self._g2 = self.gui.graph2_layout
        self._g3 = self.gui.graph3_layout
        self.selection_table.clear()

        textwidth = 45
        ### Initialize graph 1: channel time series data ###
        self._g1.setSpacing(0.)
        self._g1.setContentsMargins(0., 1., 0., 1.)
        self._ch_plots = []
        num_plots = self.channel_table.count
        for index in range(num_plots):         
            name = 'plotA{:1.0f}'.format(index+1)
            plot = self._g1.addPlot(row=index, col=0, name=name)
            axis = plot.getAxis('left')
            axis.setStyle(tickTextWidth=textwidth, autoExpandTextSpace=False)
            plot.setContentsMargins(0, 0, 2, 0)  # left, top, right, bottom
            if index == 0:
                first_plot = plot            
            if index in (1, 2, 3):
                # link x axis to first plot
                plot.setXLink(first_plot)
            if index in (0, 2, 3):
                # no bottom axis labels
                axis = plot.getAxis('bottom')
                axis.setStyle(showValues=False)
            if index == 2:
                # turn on top axis
                plot.showAxis('top', True)
                axis = plot.getAxis('top')                
                axis.setStyle(showValues=False)
            plot_info = {"ref":plot}
            self._ch_plots.append(plot_info)

        ### Initialize graph 2 - time series data for evaluation ###
        self._g2.setSpacing(0.)
        self._g2.setContentsMargins(0., 1., 0., 1.)
        self._eval_plots = []
        num_plots = self.evaluation_table.count
        for index in range(num_plots):
            name = 'plotB{:1.0f}'.format(index+1)
            plot = self._g2.addPlot(row=index, col=0, name=name)
            plot.setContentsMargins(0, 0, 2, 0)  # left, top, right, bottom
            plot.setXLink(first_plot)
            axis = plot.getAxis('left')
            axis.setStyle(tickTextWidth=textwidth, autoExpandTextSpace=False)
            if index < num_plots-1:
                plot.getAxis('bottom').setStyle(showValues=False)
            plot_info = {"ref":plot}
            self._eval_plots.append(plot_info)
            
        ### Initialize graph 3 - Allan deviations ###
        self._g3.setSpacing(0.)
        self._g3.setContentsMargins(0., 1., 0, 1.)
        self._adev_plots = []
        num_plots = 2
        # define ticks
        major = []
        minor = []
        for exp in range(-22,-8):
            value = 1*10**exp
            major.append((np.log10(value), '{:5.0E}'.format(value)))
            for factor in range(2,10,2):
                value = factor*10**exp
                minor.append((np.log10(value), '{:5.0E}'.format(value)))
        y_ticks = [ major, minor ]
        major = []
        minor = []
        for exp in range(-1,8):
            value = 1*10**exp
            if value < 1:
                major.append((np.log10(value), '{:0,.1f}'.format(value)))
            elif value < 1000000:
                major.append((np.log10(value), '{:0,.0f}'.format(value)))
            else:
                major.append((np.log10(value), '{:0,.0E}'.format(value)))
            for factor in range(2,10,2):
                value = factor*10**exp
                if value < 1:
                    minor.append((np.log10(value), '{:0,.1f}'.format(value)))
                elif value < 1000000:
                   minor.append((np.log10(value), '{:0,.0f}'.format(value)))
                else:
                    minor.append((np.log10(value), '{:0,.0E}'.format(value)))
        x_ticks = [ major, minor ]
        for index in range(num_plots):
            name = 'plotC{:1.0f}'.format(index+1)
            plot = self._g3.addPlot(row=index, col=0, name=name)
            plot.setLabel('left', text="fractional Allan deviation", units=None, unitPrefix=None)
            plot.setLabel('bottom', text="averaging interval τ  (s)", units=None, unitPrefix=None)
            plot.setContentsMargins(0, 2, 2, 0)  # left, top, right, bottom
            plot.showGrid(x=True, y=True)
            plot.showAxis('right', True)
            axis = plot.getAxis('right')
            axis.setTicks(y_ticks)
            axis.setStyle(showValues=False)
            axis = plot.getAxis('left')
            axis.setTicks(y_ticks)
            axis.setStyle(tickTextWidth=textwidth, autoExpandTextSpace=False)
            plot.showAxis('top', True)
            axis = plot.getAxis('top')
            axis.setTicks(x_ticks)            
            axis.setStyle(showValues=False)
            axis = plot.getAxis('bottom')
            axis.setTicks(x_ticks)
            axis = plot.getAxis('top')
            axis.setStyle(showValues=False)
            plot_info = {"ref":plot}
            self._adev_plots.append(plot_info)

    ###############################################################################################
    def _clicked_point(self, plot, points):
        """ callback function to handle point selection """
        del plot
        penNone = QPen(QtC.NoPen)
        penWhite = pg.mkPen(Gr.WHITE)
        penWhite.setWidth(5)
        penGray = pg.mkPen(Gr.GRAY)
        penGray.setWidth(5)
        # TODO: points do not remember their brush settings
        # TODO: therefore we should instead add our own markers we can delete later
        # TODO: get time from selected point, highlight in all plots?

        if self._points.point_b:
            self._points.point_b.setPen(penNone)
            self._points.point_b.setBrush(self._points.color_b)

        if self._points.point_a:
            self._points.point_a.setPen(penGray)
        self._points.point_b = self._points.point_a
        self._points.color_b = self._points.color_a
        self._points.point_a = points[0]
        self._points.color_a = points[0].brush()
        time = self._points.point_a.pos()[0]
        self._points.point_a.setPen(penWhite)
        self.selection_table.set_selection(time)

    ###############################################################################################
    def plot_time_series(self):
        """ update graphs of time series data """

        baselines = self.channel_table.parameters['base']
        #plots = [self._pa1, self._pa2, self._pa3, self._pa4]

        for ch_index in range(COL.CHANNELS):
            # print('plotting channel ', ch_index+1, ' data.')
            # get good data for channel
            good, range_info = self._data_obj.get_good_points(ch_index)
            self._ch_plots[ch_index]['good'] = range_info
            self._ch_plots[ch_index]['all'] = self._data_obj.ranges[ch_index]
                #print('number of good points:', good.shape)
            mskd = self._data_obj.get_mskd_points(ch_index)
                #print('selection for masked points:' ,mskd)
            rej1 = self._data_obj.get_rej1_points(ch_index)
                #print('selection for rejected points:' ,rej1)
            rej2 = self._data_obj.get_rej2_points(ch_index)
                # TODO: move initializaion of scatter plot items to GUI code
                # TODO: only remove/add points here
            sc_rej = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None))
            sc_rej.addPoints(pos=rej1, brush=Gr.YELLOW)
            sc_rej.addPoints(pos=rej2, brush=Gr.ORANGE)
            sc_rej.addPoints(pos=mskd, brush=Gr.RED)
            sc_rej.sigClicked.connect(self._clicked_point)
            # keep the good points in their own plot object, prevents disappearance
            sc_good = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None))
            sc_good.addPoints(pos=good, brush=Gr.BLUE)
            sc_good.sigClicked.connect(self._clicked_point)

            labelstring = (
                "CH "+str(ch_index+1)+"1 (Hz)<br>-"
                +str(baselines[ch_index]/1000000)+" MHz<br>"
                )
            plot = self._ch_plots[ch_index]['ref']
            plot.clear()
            plot.addItem(sc_rej)
            plot.addItem(sc_good)
            color = self.channel_table.parameters[ch_index]['color']
            labelstyle = {'color': color.name(), 'font-size': '10pt'}
            plot.setLabel(
                'left', text=labelstring, units=None, unitPrefix=None,
                **labelstyle
                )

    ###############################################################################################
    def plot_eval_time_series(self):
        """ update graphs of time series data for frequency evaluations """
        for eval_index in range(self.evaluation_table.count):
            # print('plotting data for evaluation #', eval_index+1, '.')
            # get good data for channel
            points = self._data_obj.get_evaluation_points(eval_index)
            plot = self._eval_plots[eval_index]['ref']
            color = self.evaluation_table.parameters[eval_index]['color']
            name = self.evaluation_table.parameters[eval_index]['name']
            # print('evaluation color: ', color)
            if len(points) > 1:
                sc = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None))
                sc.addPoints(pos=points, brush=color)
                sc.sigClicked.connect(self._clicked_point)
                plot.clear()
                plot.addItem(sc)
            else:
                plot.clear()
            labelstring = name+'<br>relative (Hz)<br>'
            labelstyle = {'color': color.name(), 'font-size': '10pt'}
            plot.setLabel(
                'left', text=labelstring, units=None, unitPrefix=None,
                **labelstyle
                )

    ###############################################################################################
    def zoom_good(self, qval):
        """ zoom all channel graphs to show only good data """
        del qval
        self.gui.set_status('Display only valid data')
        t_min = 1E15
        t_max = -1E15
        for plot in self._ch_plots:
            # set vertical axis for each channel:
            if plot['good']:
                plot['ref'].setYRange(plot['good']['y_min'], plot['good']['y_max'], padding=0.01)
            # find combined maxima for all time axes:
            if plot['good'] and plot['good']['t_min'] < t_min:
                t_min = plot['good']['t_min']
            if plot['good'] and plot['good']['t_max'] > t_max:
                t_max = plot['good']['t_max']
        # time axes are linked to plot 0:
        self._ch_plots[0]['ref'].setXRange(t_min, t_max, padding=0.01)
        self.gui.set_status('ok')

    ###############################################################################################
    def zoom_all(self, qval):
        """ zoom all channel graphs to show all data """
        del qval
        self.gui.set_status('Display all data')
        t_min = 1E15
        t_max = -1E15
        for plot in self._ch_plots:
            # set vertical axis for each channel:
            plot['ref'].setYRange(plot['all']['y_min'], plot['all']['y_max'], padding=0.01)
            # find combined maxima for all time axes:
            if plot['all']['t_min'] < t_min:
                t_min = plot['all']['t_min']
            if plot['all']['t_max'] > t_max:
                t_max = plot['all']['t_max']
        # time axes are linked to plot 0:
        self._ch_plots[0]['ref'].setXRange(t_min, t_max, padding=0.01)
        self.gui.set_status('ok')

    ###############################################################################################
    def plot_channel_adev(self):
        """ draw ADev graph for individual channel data """
        plot = self._adev_plots[0]['ref']
        plot.clear()
        for index in range(self.channel_table.count):
            adev = self.adev_table.channel_adev[index]
            color = self.channel_table.parameters[index]['color']
            scatter = pg.ScatterPlotItem(size=5, pen=pg.mkPen(None))
            scatter.addPoints(
                x=adev['log_taus'],
                y=adev['log_devs'],
                brush=color
                )
            plot.addItem(scatter)
        #for error_bar_plot in er_b1:
        #    plot.addItem(error_bar_plot)
        return None


        scB1 = pg.ScatterPlotItem(size=5, pen=pg.mkPen(None))
        er_b1 = []
        for index in range(self._data_obj.channels()):
            color = self.channel_color_list[index]
            (log_tau, log_dev, log_top, log_bot) = adev_obj.log_values(index)
            scB1.addPoints(x=log_tau, y=log_dev, brush=color)
            error_bar_plot = pg.ErrorBarItem(size=3, pen=Gr.SEA)
            error_bar_plot.setData(x=log_tau, y=log_dev, top=log_top, bottom=log_bot)
            er_b1.append(error_bar_plot)

        #(log_tau, log_dev, log_top, log_bot) = adev_obj.log_values(1)
        #scB1.addPoints( x=log_tau, y=log_dev, brush = Gr.PURPLE)
        #erB1b = pg.ErrorBarItem(size=3, pen=Gr.PURPLE)
        #erB1b.setData(x=log_tau, y=log_dev, top=log_top, bottom=log_bot)

        #(log_tau, log_dev, log_top, log_bot) = adev_obj.log_values(2)
        #print("dev", log_dev)
        #scB1.addPoints( x=log_tau, y=log_dev, brush = Gr.MAGENTA)
        #erB1c = pg.ErrorBarItem(size=3, pen=Gr.MAGENTA)
        #erB1c.setData(x=log_tau, y=log_dev, top=log_top, bottom=log_bot)

        #(log_tau, log_dev, log_top, log_bot) = adev_obj.log_values(3)
        #scB1.addPoints( x=log_tau, y=log_dev, brush = Gr.RED)
        #erB1d = pg.ErrorBarItem(size=3, pen=Gr.RED)
        #erB1d.setData(x=log_tau, y=log_dev, top=log_top, bottom=log_bot)



    ###############################################################################################
    def open_data_file(self, filename):
        """ load data from file, trigger eval and redraw """
        outstring = "loading file "+ filename
        self.gui.set_status(outstring)
        new_data = DataHandler(self)
        loaded_values = new_data.load_file(filename)
        outstring = "loaded "+str(loaded_values)+" values per channel."
        print(outstring)
        self.gui.set_status(outstring)
        if loaded_values > 1:
            self._data_obj = new_data
        else:
            return

        tmin_mjd = self.selection_table.set_tmin(self._data_obj.get_tmin())
        file_info = '{:s} : MJD{:6.0f}'.format(filename, tmin_mjd)
        self.gui.set_file_info(file_info)

        path, ext = os.path.splitext(filename)
        maskfile = path+'.msk'
        print('mask file candidate:', maskfile)

        outstring = "checking for mask file "+maskfile
        self.gui.set_status(outstring)
        retval, mask_count = self._data_obj.load_maskfile(maskfile)
        del retval
        outstring = str(mask_count)+" points masked"
        self.gui.set_status(outstring)
        self._filter_plot_evaluate()

    ###############################################################################
    def _filter_plot_evaluate(self):
        """ gets called on load and after manually adding to mask """
        self.gui.set_status("filtering data")
        self._data_obj.filter_data(
            self.parameters['overhangs'],
            self.parameters['threshold'],
            )
        self._data_obj.evaluate_ch_data()
        self._data_obj.evaluate_eval_data()
        self.evaluation_table.update() # has new data from evaluation call

        self.channel_table.update_view()
        # evaluate data
        self.evaluation_table.update_view()
        self.gui.set_status("plotting data")
        self.plot_time_series()
        self.gui.set_status("plotting Allan deviations")
        self.plot_channel_adev()
        self.gui.set_status("plotting evaluation data")
        self.plot_eval_time_series()
        self.gui.set_status("ok")

    ###############################################################################################
    def save_maskfile_passthru(self, qval):
        """ (re-)generate mask file to store with frequency data """
        self.gui.set_status("saving mask file")
        if not self._data_obj:
            self.gui.show_msg(
                'Failed to save mask file',
                'No data file is currently loaded.'
                )
            self.gui.set_status("failed to save mask data")
            return
        filename = self._data_obj.filename
        print('file: ', filename)
        path, ext = os.path.splitext(filename)
        maskfile = path+'.msk'
        outstring = "saving mask file " + maskfile
        self.gui.set_status(outstring)
        status, message = self._data_obj.save_maskfile(maskfile)
        self.gui.set_status("ok")
        if not status:
            self.gui.show_msg(
                "Failed to save mask file",
                "Saving mask data to file failed with message:\n"
                + message
                )
        else:
            self.gui.show_msg(
                "Save mask file",
                "Succesfully saved mask data to file:\n"
                + maskfile
                )
            self.gui.set_status("ok")

    ###############################################################################################
    def save_report_passthru(self, qval):
        del qval
        """ generate report according to current settings. Save along with configuration. """
        self.gui.set_status('generating report file')
        if not self._data_obj:
            self.gui.show_msg(
                'Failed to generate report',
                'No data file is currently loaded.'
                )
            self.gui.set_status('failed to generate report')
            return
        filename = self._data_obj.filename
        print('file: ', filename)
        path, ext = os.path.splitext(filename)
        repfile = path+'.rep'
        outstring = 'generating report file ' + repfile
        self.gui.set_status(outstring)
        status, message = self._data_obj.save_report(repfile)
        if not status:
            self.gui.show_msg(
                'Failed to generate report',
                'Generating report file failed with message:\n'
                + message
                )
            self.gui.set_status('failed to generate report')
        else:
            self.gui.show_msg(
                'Generate report file',
                'Succesfully saved report to file:\n'
                + maskfile
                )
            self.gui.set_status('ok')

    ###############################################################################################
    def save_default_config_passthru(self, qval):
        """ Save current settings to default config file. """
        del qval
        confirm = self.gui.confirm_msg('Do you really want to overwrite the default config file?')
        if confirm:
            self.gui.set_status("saving configuration file")
            # call code
        else:
            self.gui.set_status("config overwrite cancelled")

    ###############################################################################################
    def mask_selected_passthru(self, qval):
        """ Apply manual mask according to selected datapoints """
        del qval
        print("trying to add to mask")
        if not self._data_obj:
            self.gui.show_msg(
                'No data',
                'No data file is loaded. Cannot apply mask.'
                )
            return
        self.gui.set_status("Applying selected mask")
        flags = self.gui.get_mask_flags()
        tstart, tend = self.selection_table.selected_range()
        self._data_obj.add_to_mask(tstart, tend, flags)
        self.gui.set_status("Reevaluating masked data")
        self._filter_plot_evaluate()

    ###############################################################################################
    def make_color(self, colorstring):
        """ converts numpy byte string to QColor object """
        color = QColor(colorstring)
        # ??? QColor(colorstring.decode('UTF-8')) ???
#        print(
#            'converting to color: ', repr(colorstring),
#            ' --> ', color.name(), ' ', repr(color)
#            )
        return color

    ###############################################################################################
    def warning(self, title, text):
        """ allow warning messages to be posted by subroutines """
        # TODO: pass off to GUI routines. Bundle all messages received during evaluation?
        print('!! '+title+': '+text)

###################################################################################################
if __name__ == '__main__':
    #app = QApplication(sys.argv)  # pylint: disable=locally-disabled, invalid-name
    #frame = FreqEvalMain()  # pylint: disable=locally-disabled, invalid-name
    #sys.exit(app.exec_())
    pass

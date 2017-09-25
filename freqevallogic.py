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
from datahandler import DataHandler, COL, RangeInformation
from selectiontablehandler import SelectionTableModel
from channeltablehandler import ChannelTableModel
from channeladevtablehandler import ChannelADevTableModel
from evaluationtablehandler import EvaluationTableModel

class SelectedPoints(object):
    """ stores two selected points and their time values for mask selection """
    def __init__(self):
        self.point_a = None
        self.color_a = None
        self.point_b = None
        self.color_b = None

class PlotInformation(object):
    """ stores reference to individual plots and their min/max values """
    def __init__(self, reference):
        self.ref = reference
        self.good = RangeInformation()
        self.full = RangeInformation()

class FreqEvalLogic(object):
    """program logic class for frequency evaluation program"""

    BLACK = QColor('Black')
    GRAY = QColor('DarkGray')

    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.gui.set_status("Initializing backend")

        self._data_obj = None
        self._points = SelectedPoints() # initialize point selection storage

        self.channel_color_list = (
            Gr.SEA, Gr.PURPLE, Gr.MAGENTA, Gr.RED,
            Gr.ORANGE, Gr.YELLOW, Gr.GREEN
            )
        self.evaluation_color_list = (
            Gr.ORANGE, Gr.YELLOW, Gr.GREEN,
            Gr.SEA, Gr.PURPLE, Gr.MAGENTA, Gr.RED,
            )
        self.channel_ceo = 1
        self.channel_rep = 2
        self.num_channels = 4
        self.num_evaluations = 3
        self.overhangs = [1, 10] # points marked bad before/after "out-of-band" point
        self.threshold = 10

        self.eval_config = configparser.ConfigParser()
        self.eval_config['CONFIG'] = {
            'channels':str(self.num_channels),
            'outlier_threshold':str(self.threshold),
            'evaluations':str(self.num_evaluations),
            'ceo_channel':str(self.channel_ceo),
            'rep_channel':str(self.channel_rep)
        }
        for index in range(self.num_channels):
            section = 'CHANNEL{:d}'.format(index+1)
            #print("section name: "+section)
            if not section in self.eval_config:
                self.eval_config[section] = {}
            string = 'ch {:d}'.format(index+1)
            self.eval_config[section]['name'] = string
            self.eval_config[section]['color'] = self.channel_color_list[index].name()
            self.eval_config[section]['baseline'] = '0'
            self.eval_config[section]['tolerance'] = '1000'
            self.eval_config[section]['filter'] = 'yes'
            self.eval_config[section]['correction'] = '0'
            self.eval_config[section]['adev_reference'] = '1'

        for index in range(self.num_evaluations):
            section = 'EVALUATION{:d}'.format(index+1)
            if not section in self.eval_config:
                self.eval_config[section] = {}
            string = 'eval {:d}'.format(index+1)
            self.eval_config[section]['name'] = string
            index_w_offset = index+self.num_channels
            self.eval_config[section]['color'] = self.channel_color_list[index_w_offset].name()
            self.eval_config[section]['show'] = 'yes'
            self.eval_config[section]['type'] = 'absolute'
            self.eval_config[section]['multiplier'] = '1'
            self.eval_config[section]['main_comb_line'] = '1234567'
            self.eval_config[section]['main_beat_channel'] = '3'
            self.eval_config[section]['main_reference'] = '123123123123123.1234'
            self.eval_config[section]['main_sys_cor'] = '0.200'
            self.eval_config[section]['main_sys_unc'] = '0.100'
            self.eval_config[section]['ref_comb_line'] = '0'
            self.eval_config[section]['ref_beat_channel'] = '0'
            self.eval_config[section]['ref_reference'] = '123123123123123.1234'
            self.eval_config[section]['ref_sys_cor'] = '0.400'
            self.eval_config[section]['ref_sys_unc'] = '0.300'
            self.eval_config[section]['rep_rate_line'] = '4'
            self.eval_config[section]['rep_rate_channel'] = '2'

        print("reading default config file")
        self.eval_config.read('default.cfg')

        self.channel_ceo = self.eval_config['CONFIG'].getint('ceo_channel', 1)
        self.channel_rep = self.eval_config['CONFIG'].getint('rep_channel', 1)
        self.outlier_threshold = self.eval_config['CONFIG'].getfloat('outlier_threshold', 2)

        print("CEO / rep channels: ", self.channel_ceo, " / ", self.channel_rep)

        # logic class tracks table models and makes them available as needed
        self.selection_table = SelectionTableModel(None, self)

        self.channel_table = ChannelTableModel(None, self)
        self.num_channels = self.channel_table.set_from_config(self.eval_config)
        print("now ", self.num_channels, " channels known.")

        self.evaluation_table = EvaluationTableModel(None, self)
        self.num_evaluations = self.evaluation_table.set_from_config(self.eval_config)
        print("now ", self.num_evaluations, " evaluations known.")

        self.adev_table = ChannelADevTableModel(None, self)

        self.gui.set_status("Writing back to configuration file")
        with open('default.cfg', 'w') as configfile:
            self.eval_config.write(configfile)

        # initialize graph references, to be populated after logic start
        self._g1 = self._g2 = None
        self._pa1 = self._pa2 = self._pa3 = self._pa4 = None
        self._pb1 = self._pb2 = None


    def init_graphs(self):
        """ initialize graphs after GUI has been initialized """
        self.gui.set_status("Initializing graphs")
        self._g1 = self.gui.get_graph1_layout()
        self._g2 = self.gui.get_graph2_layout()

        self.selection_table.clear()

        ### Initialize graph 1 ###
        self._g1.setSpacing(0.)
        self._g1.setContentsMargins(0., 1., 0., 1.)

        textwidth = 45

        self._ch_plots = []
        plot = self._g1.addPlot(row=0, col=0, name="plotA1")
        axis = plot.getAxis('bottom')
        axis.setStyle(showValues=False)
        self._ch_plots.append(PlotInformation(plot))
        
        plot = self._g1.addPlot(row=1, col=0, name="plotA2")
        plot.setXLink(self._ch_plots[0].ref)
        self._ch_plots.append(PlotInformation(plot))
        
        plot = self._g1.addPlot(row=2, col=0, name="plotA3")
        plot.setXLink(self._ch_plots[0].ref)
        plot.showAxis('top', True)
        axis = plot.getAxis('bottom')
        axis.setStyle(showValues=False)
        axis = plot.getAxis('top')
        axis.setStyle(showValues=False)
        self._ch_plots.append(PlotInformation(plot))

        plot = self._g1.addPlot(row=3, col=0, name="plotA4")
        plot.setXLink(self._ch_plots[0].ref)
        axis = plot.getAxis('bottom')
        axis.setStyle(showValues=False)
        self._ch_plots.append(PlotInformation(plot))
        
        for plot in self._ch_plots:
            axis = plot.ref.getAxis('left')
            axis.setStyle(tickTextWidth=textwidth, autoExpandTextSpace=False)
            plot.ref.setContentsMargins(0, 0, 2, 0)  # left, top, right, bottom
        
        ### Initialize graph 2 ###
        random_x = np.arange(1000)
        random_y = np.random.normal(size=(2, 1000)) # pylint: disable=locally-disabled, no-member
        self._g2.setSpacing(0.)
        self._g2.setContentsMargins(0., 10., 0., 1.)

        self._pb1 = self._g2.addPlot(row=0, col=0, name="plotB1")
        self._pb2 = self._g2.addPlot(row=0, col=1, name="plotB2")

        self._pb1.plot(random_x, random_y[0], pen=Gr.GRAY)
        self._pb2.plot(random_x, random_y[1], pen=Gr.GRAY)

    ###############################################################################################
    def plot_time_series(self):
        """ update graphs of time series data """
        def clicked(plot, points):
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

        baselines = self.channel_table.baselines()
        #plots = [self._pa1, self._pa2, self._pa3, self._pa4]

        for ch_index in range(COL.CHANNELS):
            #print('plotting channel ',ch_index+1,' data.')
            # get good data for channel
            good, range_info = self._data_obj.get_good_points([ch_index])
            self._ch_plots[ch_index].good = range_info
            self._ch_plots[ch_index].all = self._data_obj.ranges[ch_index]
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
            sc_rej.sigClicked.connect(clicked)
            # keep the good points in their own plot object, prevents disappearance
            sc_good = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None))
            sc_good.addPoints(pos=good, brush=Gr.BLUE)
            sc_good.sigClicked.connect(clicked)

            labelstring = (
                "CH "+str(ch_index+1)+"1 (Hz)<br>-"
                +str(baselines[ch_index]/1000000)+" MHz<br>"
                )
            plot = self._ch_plots[ch_index].ref
            plot.clear()
            plot.addItem(sc_rej)
            plot.addItem(sc_good)
            labelstyle = {'color': Gr.CH_COLS[ch_index].name(), 'font-size': '10pt'}
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
            plot.ref.setYRange(plot.good.y_min, plot.good.y_max, padding=0.01)
            # find combined maxima for all time axes:        
            if plot.good.t_min < t_min:
                t_min = plot.good.t_min
            if plot.good.t_max > t_max:
                t_max = plot.good.t_max
        # time axes are linked to plot 0:
        self._ch_plots[0].ref.setXRange(t_min, t_max, padding=0.01)
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
            plot.ref.setYRange(plot.all.y_min, plot.all.y_max, padding=0.01)
            # find combined maxima for all time axes:        
            if plot.all.t_min < t_min:
                t_min = plot.all.t_min
            if plot.all.t_max > t_max:
                t_max = plot.all.t_max
        # time axes are linked to plot 0:
        self._ch_plots[0].ref.setXRange(t_min, t_max, padding=0.01)
        self.gui.set_status('ok')        

    ###############################################################################################
    def plot_channel_adev(self, adev_obj):
        """ draw ADev graph for individual channel data """
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

        self._pb1.clear()
        self._pb1.addItem(scB1)
        for error_bar_plot in er_b1:
            self._pb1.addItem(error_bar_plot)
        #self._pb1.addItem(erB1a)
        #self._pb1.addItem(erB1b)
        #self._pb1.addItem(erB1c)
        #self._pb1.addItem(erB1d)
        self._pb1.setLabel('left', text="fractional ADev", units=None, unitPrefix=None)
        self._pb1.setLabel('bottom', text="time (s)", units=None, unitPrefix=None)

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
        self._data_obj.filter_data(self.overhangs, self.outlier_threshold)
        self.channel_table.update_view()
        # evaluate data
        self.evaluation_table.update_view()
        self.gui.set_status("plotting data")
        self.plot_time_series()
        self.gui.set_status("calculating Allan deviations")
        adev_obj = self._data_obj.channel_adev()
        self.plot_channel_adev(adev_obj)
        self.gui.set_status("ok")



    ###############################################################################
    #def save_maskfile(self, qval):
    #    """ initiate saving of mask file """
    #    del qval
    #    status, message = self._logic.save_maskfile()
    #    if status:
    #        QMessageBox.about(self, "Saved mask data", "Succesfully saved mask data to file.")
    #    else:
    #        outstring = (
    #            "Saving mask data failed with error message:\n"
    #            + message
    #            )
    #        QMessageBox.about(self, "Error saving mask data", outstring)

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
    def set_channel_color_list(self, clist):
        """ update list of colors used for channel plots """
        length = len(clist)
        self.channel_color_list = [QColor(colorstring) for colorstring in clist]
        #for color in self.channel_color_list:
        #    print("color ",color.name())

    ###############################################################################################
    def set_evaluation_color_list(self, clist):
        """ update list of colors used for evaluation plots """
        length = len(clist)
        self.evaluation_color_list = [QColor(colorstring) for colorstring in clist]
        #for color in self.channel_color_list:
        #    print("color ",color.name())

    ###############################################################################################
    def warning(self, title, text):
        """ allow warning messages to be posted by subroutines """
        # TODO: pass off to GUI routines. Bundle all messages received during evaluation?
        print(title)
        print(text)

###################################################################################################
if __name__ == '__main__':
    #app = QApplication(sys.argv)  # pylint: disable=locally-disabled, invalid-name
    #frame = FreqEvalMain()  # pylint: disable=locally-disabled, invalid-name
    #sys.exit(app.exec_())
    pass

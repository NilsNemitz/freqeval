#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Main logic code for frequency evaluation program
Created on 2017/09/04
@author: Nils Nemitz
"""

# py#lint: disable=locally-disabled, redefined-variable-type
# pylint: disable=locally-disabled, too-many-instance-attributes

import configparser
import pyqtgraph_core as pg
from PyQt5.QtGui import QColor # pylint: disable=locally-disabled, no-name-in-module
# import pandas
import numpy as np
# import math

from freqevalconstants import Gr # color definitions
from datahandler import DataHandler, COL
from channeltablehandler import ChannelTableModel
from channeladevtablehandler import ChannelADevTableModel
from evaluationtablehandler import EvaluationTableModel

class SelectedPoints(object):
    """stores two selected points and there time values for mask selection"""
    def __init__(self):
        self.point_a = None
        self.point_b = None
        self.time_a = None
        self.time_b = None


class FreqEvalLogic(object):
    """program logic class for frequency evaluation program"""

    def __init__(self, gui):
        super().__init__()
        self.gui = gui
        self.gui.set_status("Initializing backend")

        self._filename = None
        self._data_obj = None
        self._points = SelectedPoints() # initialize point selection storage

        self.channel_color_list = (Gr.SEA, Gr.PURPLE, Gr.MAGENTA, Gr.RED)
        self.num_channels = 4
        self.num_evaluations = 2

        self.eval_config = configparser.ConfigParser()
        self.eval_config['CONFIG']={
            'channels':str(self.num_channels),
            'outlier_threshold':'5',
            'evaluations':str(self.num_evaluations)            
        }
        for index in range(self.num_channels):
            section = 'CHANNEL{:d}'.format(index+1)
            #print("section name: "+section)
            if not section in self.eval_config:
                self.eval_config[section]={}
            string = 'ch {:d}'.format(index+1)
            self.eval_config[section]['name'] = string
            self.eval_config[section]['color'] = self.channel_color_list[index].name()
            self.eval_config[section]['baseline'] = '0'
            self.eval_config[section]['tolerance'] = '1000'
            self.eval_config[section]['filter'] = 'yes'
            self.eval_config[section]['correction'] = '0'
            self.eval_config[section]['adev_reference'] = '1'

        print("reading default config file")
        self.eval_config.read('default.cfg')

        # logic class tracks table models and makes them available as needed
        self.channel_table = ChannelTableModel(None, self)
        self.num_channels = self.channel_table.set_from_config(self.eval_config)
        print("now ",self.num_channels," known.")
        
        self.evaluation_table = EvaluationTableModel(None, self)
        self.adev_table = ChannelADevTableModel(None, self)

        print("trying to write back to config file")
        with open('default.cfg','w') as configfile:
            self.eval_config.write(configfile)

        self._g1 = self._g2 = None
        self._pa1 = self._pa2 = self._pa3 = self._pa4 = None


    def init_graphs(self):
        """ initialize graphs after GUI has been initialized """
        self.gui.set_status("Initializing graphs")
        self._g1 = self.gui.get_graph1_layout()
        self._g2 = self.gui.get_graph2_layout()

        ### Initialize graph 1 ###
        self._g1.setSpacing(0.)
        self._g1.setContentsMargins(0., 1., 0., 1.)

        textwidth = 45

        self._pa1 = self._g1.addPlot(row=0, col=0, name="plotA1")
        axis = self._pa1.getAxis('bottom')
        axis.setStyle(showValues=False)
        axis = self._pa1.getAxis('left')
        axis.setStyle(tickTextWidth=textwidth, autoExpandTextSpace=False)

        self._pa2 = self._g1.addPlot(row=1, col=0, name="plotA2")
        self._pa2.setXLink(self._pa1)
        axis = self._pa2.getAxis('left')
        axis.setStyle(tickTextWidth=textwidth, autoExpandTextSpace=False)

        self._pa3 = self._g1.addPlot(row=2, col=0, name="plotA3")
        self._pa3.setXLink(self._pa1)
        self._pa3.showAxis('top', True)
        axis = self._pa3.getAxis('bottom')
        axis.setStyle(showValues=False)
        axis = self._pa3.getAxis('top')
        axis.setStyle(showValues=False)
        axis = self._pa3.getAxis('left')
        axis.setStyle(tickTextWidth=textwidth, autoExpandTextSpace=False)

        self._pa4 = self._g1.addPlot(row=3, col=0, name="plotA4")
        self._pa4.setXLink(self._pa1)
        axis = self._pa4.getAxis('bottom')
        axis.setStyle(showValues=False)
        axis = self._pa4.getAxis('left')
        axis.setStyle(tickTextWidth=textwidth, autoExpandTextSpace=False)

        self._pa1.setContentsMargins(0, 0, 2, 0)  # left, top, right, bottom
        self._pa2.setContentsMargins(0, 0, 2, 0)
        self._pa3.setContentsMargins(0, 0, 2, 0)
        self._pa4.setContentsMargins(0, 0, 2, 0)

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
        good = self._data_obj.get_good_points()
        mskd = self._data_obj.get_mskd_points()
        rej1 = self._data_obj.get_rej1_points()
        rej2 = self._data_obj.get_rej2_points()
        rej3 = self._data_obj.get_rej3_points()
        print("types: ", len(good), " ", len(mskd), " ", len(rej1), " ", len(rej2), " ", len(rej3))

        baselines = self.channel_table.baselines()

        sc_a1 = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None))
        sc_a1.addPoints(pos=rej1[:, (COL.TIME, COL.CH1)], brush=Gr.BROWN)
        sc_a1.addPoints(pos=rej2[:, (COL.TIME, COL.CH1)], brush=Gr.ORANGE)
        sc_a1.addPoints(pos=rej3[:, (COL.TIME, COL.CH1)], brush=Gr.YELLOW)
        # keep the good points in there own plot object, prevents disappearance
        sc_a1_m = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None))
        sc_a1_m.addPoints(pos=good[:, (COL.TIME, COL.CH1)], brush=Gr.BLUE)

        labelstring = "CH 1 (Hz)<br>-"+str(baselines[0]/1000000)+" MHz<br>"
        self._pa1.clear()
        self._pa1.addItem(sc_a1)
        self._pa1.addItem(sc_a1_m)
        labelstyle = {'color': Gr.CH_COLS[0].name(), 'font-size': '10pt'}
        self._pa1.setLabel('left', text=labelstring, units=None, unitPrefix=None, **labelstyle)

        sc_a2 = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None))
        sc_a2.addPoints(pos=rej1[:, (COL.TIME, COL.CH2)], brush=Gr.BROWN)
        sc_a2.addPoints(pos=rej2[:, (COL.TIME, COL.CH2)], brush=Gr.ORANGE)
        sc_a2.addPoints(pos=rej3[:, (COL.TIME, COL.CH2)], brush=Gr.YELLOW)
        sc_a2_m = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None))
        sc_a2_m.addPoints(pos=good[:, (COL.TIME, COL.CH2)], brush=Gr.BLUE)
        labelstyle = {'color': Gr.CH_COLS[1].name(), 'font-size': '10pt'}
        labelstring = "CH 2 (Hz)<br>-"+str(baselines[1]/1000000)+" MHz<br>"
        self._pa2.clear()
        self._pa2.addItem(sc_a2)
        self._pa2.addItem(sc_a2_m)
        self._pa2.setLabel('left', text=labelstring, units=None, unitPrefix=None, **labelstyle)

        sc_a3 = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None))
        sc_a3.addPoints(pos=rej1[:, (COL.TIME, COL.CH3)], brush=Gr.BROWN)
        sc_a3.addPoints(pos=rej2[:, (COL.TIME, COL.CH3)], brush=Gr.ORANGE)
        sc_a3.addPoints(pos=rej3[:, (COL.TIME, COL.CH3)], brush=Gr.YELLOW)
        sc_a3_m = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None))
        sc_a3_m.addPoints(pos=good[:, (COL.TIME, COL.CH3)], brush=Gr.BLUE)
        labelstyle = {'color': Gr.CH_COLS[2].name(), 'font-size': '10pt'}
        labelstring = "CH 3 (Hz)<br>-"+str(baselines[2]/1000000)+" MHz<br>"
        self._pa3.clear()
        self._pa3.addItem(sc_a3)
        self._pa3.addItem(sc_a3_m)
        self._pa3.setLabel('left', text=labelstring, units=None, unitPrefix=None, **labelstyle)

        sc_a4 = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None))
        sc_a4.addPoints(pos=rej1[:, (COL.TIME, COL.CH4)], brush=Gr.BROWN)
        sc_a4.addPoints(pos=rej2[:, (COL.TIME, COL.CH4)], brush=Gr.ORANGE)
        sc_a4.addPoints(pos=rej3[:, (COL.TIME, COL.CH4)], brush=Gr.YELLOW)
        sc_a4_m = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None))
        sc_a4_m.addPoints(pos=good[:, (COL.TIME, COL.CH4)], brush=Gr.BLUE)
        labelstyle = {'color': Gr.CH_COLS[3].name(), 'font-size': '10pt'}
        labelstring = "CH 4 (Hz)<br>-"+str(baselines[3]/1000000)+" MHz<br>"
        self._pa4.clear()
        self._pa4.addItem(sc_a4)
        self._pa4.addItem(sc_a4_m)
        self._pa4.setLabel('left', text=labelstring, units=None, unitPrefix=None, **labelstyle)

        def clicked(plot, points):
            """ callback function to handle point selection """
            del plot
            if self._points.point_b:
                self._points.point_b.setPen(None)
            if self._points.point_a:
                self._points.point_a.setPen(Gr.GRAY)
            self._points.point_b = self._points.point_a
            # allow keeping time value even if points get deselected:
            self._points.time_b = self._points.time_a
            self._points.point_a = points[0]
            # allow keeping time value even if points get deselected:
            self._points.time_a = self._points.point_a.pos()[0]
            self._points.point_a.setPen(Gr.WHITE)
            print(
                "clicked point at ", self._points.point_a.pos(),
                " set time to ", self._points.time_a
                )
        sc_a1.sigClicked.connect(clicked)
        sc_a2.sigClicked.connect(clicked)
        sc_a3.sigClicked.connect(clicked)
        sc_a4.sigClicked.connect(clicked)
        sc_a1_m.sigClicked.connect(clicked)
        sc_a2_m.sigClicked.connect(clicked)
        sc_a3_m.sigClicked.connect(clicked)
        sc_a4_m.sigClicked.connect(clicked)


    ###############################################################################################
    def plot_channel_adev(self, adev_obj):
        """ draw ADev graph for individual channel data """
        scB1 = pg.ScatterPlotItem(size=5, pen=pg.mkPen(None))
        er_b1 = []
        for index in range(self._data_obj.channels()):
            color = self.channel_color_list[index]
            (log_tau, log_dev, log_top, log_bot) = adev_obj.log_values(index)
            scB1.addPoints( x=log_tau, y=log_dev, brush=color)
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
        self._pb1.setLabel('left',text="fractional ADev", units=None, unitPrefix=None)
        self._pb1.setLabel('bottom',text="time (s)", units=None, unitPrefix=None)        

    ###############################################################################################
    def open_data_file(self, filename):
        """ load data from file, trigger eval and redraw """
        print("load file ",filename)
        new_data = DataHandler(self)
        loaded_values = new_data.load_file(filename)
        print("loaded ",loaded_values," values per channel.")
        if loaded_values > 1:
            self._data_obj = new_data
            self._filename = filename

        self.plot_time_series()
        
        adev_obj = self._data_obj.channel_adev()
        self.plot_channel_adev(adev_obj)

    ###############################################################################################
    def save_report(self):
        """ generate report according to current settings. Save along with configuration. """
        self.gui.set_status("saving configuration file")
        
        self.gui.set_status("generating report")
        self.gui.set_status("saving report")
        self.gui.set_status("ok")        
        return 0

    ###############################################################################################
    def save_default_config(self):
        """ Save current settings to default config file. """
        self.gui.set_status("saving configuration file")
        self.gui.set_status("ok")        
        return 0

    ###############################################################################################
    def set_channel_color_list(self, clist):
        length = len(clist)
        self.channel_color_list = [QColor(colorstring) for colorstring in clist]
        for color in self.channel_color_list:
            print("color ",color.name())        

###################################################################################################
if __name__ == '__main__':
    #app = QApplication(sys.argv)  # pylint: disable=locally-disabled, invalid-name
    #frame = FreqEvalMain()  # pylint: disable=locally-disabled, invalid-name
    #sys.exit(app.exec_())
    pass

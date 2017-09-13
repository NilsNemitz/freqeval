#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Main logic code for frequency evaluation program
Created on 2017/09/04
@author: Nils Nemitz
"""

# pylint: disable=locally-disabled, redefined-variable-type
# pylint: disable=locally-disabled, too-many-instance-attributes

import pyqtgraph_core as pg
import pandas
import numpy as np
import math

from datahandler import DataHandler, COL
from freqevalconstants import Gr # color definitions


class SelectedPoints(object):
    """stores two selected points and there time values for mask selection"""
    def __init__(self):
        self.pointA = None
        self.pointB = None
        self.timeA = None
        self.timeB = None

class FreqEvalLogic(object):
    """main class for frequency evaluation program"""

    def __init__(self, gui):
        super().__init__()
        self.gui = gui

        # channel table is only used to label graphs with baselines
        # mostly passed through to datahandler
        self.channel_table = gui.channel_table()
        self.gui.set_status("Initializing")

        self.points = SelectedPoints() # initialize point selection storage

        self.g1 = self.gui.get_graph1_layout()
        self.g2 = self.gui.get_graph2_layout()
        data = None

        ### Initialize graph 1 ###
        self.g1.setSpacing(0.)
        self.g1.setContentsMargins(0., 1., 0., 1.)

        textwidth = 45

        pA1 = self.g1.addPlot(row=0, col=0, name="plotA1")
        self.pA1 = pA1
        axis = pA1.getAxis('bottom')
        axis.setStyle(showValues = False)
        axis = pA1.getAxis('left')
        axis.setStyle(tickTextWidth = textwidth, autoExpandTextSpace = False)
        
        pA2 = self.g1.addPlot(row=1, col=0, name="plotA2")
        pA2.setXLink(pA1)
        self.pA2 = pA2
        axis = pA2.getAxis('left')
        axis.setStyle( tickTextWidth = textwidth, autoExpandTextSpace = False )
        
        pA3 = self.g1.addPlot(row=2, col=0, name="plotA3")
        pA3.setXLink(pA1)        
        pA3.showAxis('top',True)
        self.pA3 = pA3
        axis = pA3.getAxis('bottom')
        axis.setStyle( showValues = False )
        axis = pA3.getAxis('top')
        axis.setStyle( showValues = False )
        axis = pA3.getAxis('left')
        axis.setStyle( tickTextWidth = textwidth, autoExpandTextSpace = False )

        pA4 = self.g1.addPlot(row=3, col=0, name="plotA4")        
        pA4.setXLink(pA1)
        self.pA4 = pA4
        axis = pA4.getAxis('bottom')
        axis.setStyle( showValues = False )
        axis = pA4.getAxis('left')
        axis.setStyle( tickTextWidth = textwidth, autoExpandTextSpace = False )
        
        pA1.setContentsMargins( 0, 0, 2, 0)  # left, top, right, bottom
        pA2.setContentsMargins( 0, 0, 2, 0)
        pA3.setContentsMargins( 0, 0, 2, 0)
        pA4.setContentsMargins( 0, 0, 2, 0)
        
        ### Initialize graph 2 ###    
        x = np.arange(1000)
        y = np.random.normal(size=(2, 1000))
        self.g2.setSpacing(0.)
        self.g2.setContentsMargins(0., 10., 0., 1.)
        
        self.pB1 = self.g2.addPlot(row=0, col=0, name="plotB1")
        self.pB2 = self.g2.addPlot(row=0, col=1, name="plotB2")
        
        self.pB1.plot(x, y[0], pen=Gr.GRAY)
        self.pB2.plot(x, y[1], pen=Gr.GRAY)

    ###############################################################################################
    def plot_time_series(self):
        """ update graphs of time series data """
        good = self.data_obj.get_good_points()
        mskd = self.data_obj.get_mskd_points()
        rej1 = self.data_obj.get_rej1_points()
        rej2 = self.data_obj.get_rej2_points()
        rej3 = self.data_obj.get_rej3_points()
        print("types: ", len(good), " ", len(mskd), " ", len(rej1), " ", len(rej2), " ", len(rej3))

        #penBlue  = pg.mkPen( 87, 187, 187)
        #penMarkA = pg.mkPen(255, 255, 255, width = 5)  
        #penMarkB = pg.mkPen(192, 192, 192, width = 5)  
        #brushBlue   = pg.mkBrush( 87, 187, 187) 
        #brushYellow = pg.mkBrush(241, 192,  38) 
        #brushOrange = pg.mkBrush(213, 121,  19) 
        #brushBrown  = pg.mkBrush(153,  84,  21)  

        baselines = self.channel_table.baselines()

        scA1 = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None) )
        scA1.addPoints( pos=rej1[:,(COL.TIME, COL.CH1)], brush = Gr.BROWN )
        scA1.addPoints( pos=rej2[:,(COL.TIME, COL.CH1)], brush = Gr.ORANGE )
        scA1.addPoints( pos=rej3[:,(COL.TIME, COL.CH1)], brush = Gr.YELLOW )
        # keep the good points in there own plot object, prevents disappearance
        scA1m = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None) )
        scA1m.addPoints( pos=good[:,(COL.TIME, COL.CH1)], brush = Gr.BLUE )
        
        labelstring = "CH 1 (Hz)<br>-"+str(baselines[0]/1000000)+" MHz<br>"
        self.pA1.clear()
        self.pA1.addItem(scA1)
        self.pA1.addItem(scA1m)
        labelstyle = {'color': Gr.CH_COLS[0].name(), 'font-size': '10pt'}
        self.pA1.setLabel('left',text=labelstring, units=None, unitPrefix=None, **labelstyle)
        
        scA2 = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None) )
        scA2.addPoints( pos=rej1[:,(COL.TIME, COL.CH2)], brush = Gr.BROWN )
        scA2.addPoints( pos=rej2[:,(COL.TIME, COL.CH2)], brush = Gr.ORANGE )
        scA2.addPoints( pos=rej3[:,(COL.TIME, COL.CH2)], brush = Gr.YELLOW )
        scA2m = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None) )
        scA2m.addPoints( pos=good[:,(COL.TIME, COL.CH2)], brush = Gr.BLUE )
        labelstyle = {'color': Gr.CH_COLS[1].name(), 'font-size': '10pt'}
        labelstring = "CH 2 (Hz)<br>-"+str(baselines[1]/1000000)+" MHz<br>"
        self.pA2.clear()
        self.pA2.addItem(scA2)
        self.pA2.addItem(scA2m)        
        self.pA2.setLabel('left',text=labelstring, units=None, unitPrefix=None, **labelstyle)

        scA3 = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None) )
        scA3.addPoints( pos=rej1[:,(COL.TIME, COL.CH3)], brush = Gr.BROWN )
        scA3.addPoints( pos=rej2[:,(COL.TIME, COL.CH3)], brush = Gr.ORANGE )
        scA3.addPoints( pos=rej3[:,(COL.TIME, COL.CH3)], brush = Gr.YELLOW )
        scA3m = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None) )
        scA3m.addPoints( pos=good[:,(COL.TIME, COL.CH3)], brush = Gr.BLUE )
        print("color")
        print(Gr.BROWN.name())        
        print(Gr.CH_COLS[0].name())
        labelstyle = {'color': Gr.CH_COLS[2].name(), 'font-size': '10pt'}
        labelstring = "CH 3 (Hz)<br>-"+str(baselines[2]/1000000)+" MHz<br>"
        self.pA3.clear()
        self.pA3.addItem(scA3)
        self.pA3.addItem(scA3m)
        self.pA3.setLabel('left',text=labelstring, units=None, unitPrefix=None, **labelstyle)

        scA4 = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None) )
        scA4.addPoints( pos=rej1[:,(COL.TIME, COL.CH4)], brush = Gr.BROWN )
        scA4.addPoints( pos=rej2[:,(COL.TIME, COL.CH4)], brush = Gr.ORANGE )
        scA4.addPoints( pos=rej3[:,(COL.TIME, COL.CH4)], brush = Gr.YELLOW )
        scA4m = pg.ScatterPlotItem(size=4, pen=pg.mkPen(None) )
        scA4m.addPoints( pos=good[:,(COL.TIME, COL.CH4)], brush = Gr.BLUE )
        labelstyle = {'color': Gr.CH_COLS[3].name(), 'font-size': '10pt'}
        labelstring = "CH 4 (Hz)<br>-"+str(baselines[3]/1000000)+" MHz<br>"
        self.pA4.clear()
        self.pA4.addItem(scA4)
        self.pA4.addItem(scA4m)
        self.pA4.setLabel('left',text=labelstring, units=None, unitPrefix=None, **labelstyle)

        def clicked(plot, points):
            if self.points.pointB:
                self.points.pointB.setPen( None )
            if self.points.pointA:            
                self.points.pointA.setPen( Gr.GRAY )  
            self.points.pointB = self.points.pointA
            self.points.timeB = self.points.timeA # allow keeping time value even if points get deselected
            self.points.pointA = points[0]
            self.points.timeA = self.points.pointA.pos()[0] # allow keeping time value even if points get deselected
            self.points.pointA.setPen( Gr.WHITE )            
            print( "clicked point at ", self.points.pointA.pos()," set time to ",self.points.timeA )            

        scA1.sigClicked.connect(clicked)
        scA2.sigClicked.connect(clicked)
        scA3.sigClicked.connect(clicked)
        scA4.sigClicked.connect(clicked)
        scA1m.sigClicked.connect(clicked)
        scA2m.sigClicked.connect(clicked)
        scA3m.sigClicked.connect(clicked)
        scA4m.sigClicked.connect(clicked)


    ###############################################################################################
    def plot_channel_ADev(self, adev_obj):
        """ draw ADev graph for individual channel data """
        #brushBlue   = pg.mkBrush( 87, 187, 187) 
        #penBlue   = pg.mkPen( 87, 187, 187, width=3) 
        #brushYellow = pg.mkBrush(241, 192,  38) 
        #brushOrange = pg.mkBrush(213, 121,  19) 
        #brushBrown  = pg.mkBrush(153,  84,  21)  

        scB1 = pg.ScatterPlotItem(size=5, pen=pg.mkPen(None))
        
        (log_tau, log_dev, log_top, log_bot) = adev_obj.log_values(0)
        scB1.addPoints( x=log_tau, y=log_dev, brush = Gr.SEA )
        erB1a = pg.ErrorBarItem(size=3, pen=Gr.SEA)
        erB1a.setData(x=log_tau, y=log_dev, top=log_top, bottom=log_bot)

        (log_tau, log_dev, log_top, log_bot) = adev_obj.log_values(1)
        scB1.addPoints( x=log_tau, y=log_dev, brush = Gr.PURPLE )
        erB1b = pg.ErrorBarItem(size=3, pen=Gr.PURPLE)
        erB1b.setData(x=log_tau, y=log_dev, top=log_top, bottom=log_bot)

        (log_tau, log_dev, log_top, log_bot) = adev_obj.log_values(2)
        print("dev", log_dev)
        scB1.addPoints( x=log_tau, y=log_dev, brush = Gr.MAGENTA )
        erB1c = pg.ErrorBarItem(size=3, pen=Gr.MAGENTA)
        erB1c.setData(x=log_tau, y=log_dev, top=log_top, bottom=log_bot)
        
        (log_tau, log_dev, log_top, log_bot) = adev_obj.log_values(3)
        scB1.addPoints( x=log_tau, y=log_dev, brush = Gr.RED )
        erB1d = pg.ErrorBarItem(size=3, pen=Gr.RED)
        erB1d.setData(x=log_tau, y=log_dev, top=log_top, bottom=log_bot)
        
        labelstring = "ADev (Hz)"
        self.pB1.clear()
        self.pB1.addItem(scB1)
        self.pB1.addItem(erB1a)
        self.pB1.addItem(erB1b)
        self.pB1.addItem(erB1c)
        self.pB1.addItem(erB1d)
        self.pB1.setLabel('left',text="ADev (Hz)", units=None, unitPrefix=None)
        self.pB1.setLabel('bottom',text="time (s)", units=None, unitPrefix=None)        

    ###############################################################################################
    def open_data_file(self, filename):
        """ load data from file, trigger eval and redraw """
        print("load file ",filename)
        new_data = DataHandler(self.channel_table)
        loaded_values = new_data.load_file(filename)
        print("loaded ",loaded_values," values per channel.")
        self.data_obj = new_data

        self.plot_time_series()
        
        adev_obj = self.data_obj.channel_adev()
        self.plot_channel_ADev(adev_obj)


if __name__ == '__main__':
    #app = QApplication(sys.argv)  # pylint: disable=locally-disabled, invalid-name
    #frame = FreqEvalMain()  # pylint: disable=locally-disabled, invalid-name
    #sys.exit(app.exec_())
    pass

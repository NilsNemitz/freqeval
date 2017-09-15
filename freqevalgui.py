#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Main GUI code for frequency evaluation program
Created on 2017/09/03
@author: Nils Nemitz
"""

# py#lint: disable=locally-disabled, redefined-variable-type
# pylint: disable=locally-disabled, too-many-instance-attributes

# import sys

import os

from PyQt5 import ( # pylint: disable=locally-disabled, no-name-in-module
    QtGui, QtCore, QtWidgets
    )
from PyQt5.QtWidgets import ( # pylint: disable=locally-disabled, no-name-in-module
    QMainWindow, QMessageBox,
    #QApplication, QWidget, #QPlainTextEdit,
    QFrame, QLabel, QTableView,
    #qApp,
    QFileDialog,
    QAction,
    #QHBoxLayout,
    QVBoxLayout,
    #QGridLayout,
    QSplitter, QScrollArea,
    QSizePolicy
    )
from PyQt5.QtCore import ( # pylint: disable=locally-disabled, no-name-in-module
    QSettings, Qt
    )
#from PyQt5.QtGui import ( # pylint: disable=locally-disabled, no-name-in-module
#    QTextOption
#    )

import pyqtgraph_core as pg

from freqevallogic import FreqEvalLogic

class FreqEvalMain(QMainWindow):
    """main class widget for comb counter readout program"""
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowIcon(QtGui.QIcon(QtGui.QPixmap(logo()))) # pylint: disable=locally-disabled, no-member
        self._settings = QSettings('freqeval.ini', QSettings.IniFormat)
        self._settings.setFallbacksEnabled(False)
        # configuration constants
        self._logic = FreqEvalLogic(self)
        self.init_gui()
        self._logic.init_graphs()
        self.show()
        self.init_state() # code in init_state has access to logic already
        self._base_path = self._settings.value('basepath', "")

    ###############################################################################
    def show_msg_not_implemented(self, qval):
        """show dialog indicating not-yet-implemented feature"""
        del qval
        QMessageBox.about(self, "Not implemented", "This function is not yet implemented.")

    ###############################################################################
    def redraw(self, qval):
        """ manually trigger window redraw """
        del qval
        print("forced redraw")
        self._channel_table_view.update()
        self._graph_widget.update()
        #self._channel_table_view.refresh()
        self._graph_widget.refresh()
        self._main_widget.refresh()

    ###############################################################################
    def select_data_file(self, qval):
        """select a file and trigger loading"""
        del qval
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open data file",
            self._base_path,
            "CSV Data Files (*.csv);;All Files (*)",
            options=options
            )
        if filename:
            self._base_path = os.path.dirname(filename)
            self._logic.open_data_file(filename) # trigger file loading

    ###############################################################################
    def save_report(self, qval):
        """ save associated config file, generate and save report """
        del qval
        status = self._logic.save_report()
        if status == -2:
            QMessageBox.about(self, "Report generation", "No data file is currently open.")
        elif status == -1:
            QMessageBox.about(self, "Report generation", "Report generation failed.")
        elif status == 0:
            QMessageBox.about(
                self, "Report generation",
                "Report was successfully generated and saved along with current configuration."
            )

    ###############################################################################
    def save_default_config(self, qval):
        """ save associated config file, generate and save report """
        del qval
        status = self._logic.save_default_config()
        if status == -1:
            QMessageBox.about(
                self, "Configuration",
                "Updating default configuration file failed."
            )
        if status == 0:
            QMessageBox.about(
                self, "Configuration",
                "Default configuration file has been updated with current settings."
            )

    ###############################################################################
    def init_gui(self):
        """initialize and load basic settings for UI"""
        self.setWindowTitle('Frequency Evaluation for Comb Count')
        self.resize(self._settings.value('windowsize', QtCore.QSize(270, 225))) # pylint: disable=locally-disabled, no-member
        self.move(self._settings.value('windowposition', QtCore.QPoint(50, 50))) # pylint: disable=locally-disabled, no-member

        ### set up menus #########################################################
        menubar = self.menuBar()

        open_act = QAction('&Open', self)
        open_act.setShortcut('Ctrl+O')
        open_act.setStatusTip('Open data file')
        open_act.triggered.connect(self.select_data_file)

        report_act = QAction('Save &report', self)
        report_act.setShortcut('Ctrl+R')
        report_act.setStatusTip('Save report and config for current data file')
        report_act.triggered.connect(self.save_report)

        save_config_act = QAction('Save &default config', self)
        #save_config_act.setShortcut('Ctrl+O')
        save_config_act.setStatusTip('Save current channel and evaluation configuration as default')
        save_config_act.triggered.connect(self.save_default_config)

        exit_act = QAction('&Exit', self)
        exit_act.setShortcut('Ctrl+Q')
        exit_act.setStatusTip('Exit application')
        exit_act.triggered.connect(self.close)

        file_menu = menubar.addMenu('&File')
        file_menu.addAction(open_act)
        file_menu.addAction(report_act)
        file_menu.addAction(save_config_act)
        file_menu.addAction(exit_act)

        mask_act = QAction('&Mask selected', self)
        mask_act.setShortcut('Ctrl+M')
        mask_act.setStatusTip('Mask data between selected points')

        edit_mask_act = QAction('((&Edit masks))', self)
        edit_mask_act.setStatusTip('Edit list of applied masks')
        edit_mask_act.setChecked(True)
        edit_mask_act.triggered.connect(self.show_msg_not_implemented)

        mask_menu = menubar.addMenu('((&Mask))')
        mask_menu.addAction(mask_act)
        mask_menu.addAction(edit_mask_act)

        view_all_act = QAction('((View &all))', self)
        view_all_act.setShortcut('Ctrl+A')
        view_all_act.setStatusTip('View all data')
        view_all_act.triggered.connect(self.show_msg_not_implemented)

        zoom_good_act = QAction('((&Zoom good data))', self)
        zoom_good_act.setShortcut('Ctrl+Z')
        zoom_good_act.setStatusTip('Zoom in to show only good data')
        zoom_good_act.triggered.connect(self.show_msg_not_implemented)

        redraw_act = QAction('&Redraw', self)
        redraw_act.setShortcut('Ctrl+R')
        redraw_act.setStatusTip('Redraw window')
        redraw_act.triggered.connect(self.redraw)

        mask_menu = menubar.addMenu('&View')
        mask_menu.addAction(view_all_act)
        mask_menu.addAction(zoom_good_act)
        mask_menu.addAction(redraw_act)

        #self.settings.setValue('windowposition', self.pos())
        #self.settings.setValue('windowsize', self.size())
        #self._size_combo = QComboBox()
        #self._size_combo.addItem("18 pt", 18)
        #self._size_combo.addItem("100 pt", 100)
        #self._size_combo.setCurrentIndex(-1)
        #self._size_combo.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        #self._size_combo.currentIndexChanged.connect(self.size_combo_changed)

        ### sub-frame for time series graphs (upper region) ###
        self.graph1_layout = pg.GraphicsLayout()
        self.graph1_layout.setSpacing(0.)
        self.graph1_layout.setContentsMargins(0., 1., 0., 1.)
        graph1 = pg.GraphicsView()
        graph1.setCentralItem(self.graph1_layout)

        ### sub-frame for ADev graph (bottom region) ###
        self.graph2_layout = pg.GraphicsLayout()
        self.graph2_layout.setSpacing(0.)
        self.graph2_layout.setContentsMargins(0., 10., 0., 0.)
        graph2 = pg.GraphicsView()
        graph2.setCentralItem(self.graph2_layout)

        ### scrollable sub-frame for results and configuration tables
        channel_table_title_label = QLabel("Channel settings")
        channel_table_title_label.setStyleSheet("font-weight: bold;")
        ch_adev_table_title_label = QLabel("Allan Deviation results")
        ch_adev_table_title_label.setStyleSheet("font-weight: bold;")
        evaluation_table_title_label = QLabel("Evaluation settings and results")
        evaluation_table_title_label.setStyleSheet("font-weight: bold;")

        row_height = 24
        ### table for channel parameters
        self._channel_table_view = QTableView()
        self._channel_table_view.setModel(self._logic.channel_table)
        self._channel_table_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._channel_table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        vertical_header = self._channel_table_view.verticalHeader()
        vertical_header.setSectionResizeMode(QtWidgets.QHeaderView.Fixed) # pylint: disable=locally-disabled, no-member
        vertical_header.setMaximumSectionSize(row_height)
        #vertical_header.setDefaultAlignment(Qt.AlignCenter)
        self._channel_table_view.resizeRowsToContents()
        self._channel_table_view.resizeColumnsToContents()
        vheader = self._channel_table_view.verticalHeader()
        hheader = self._channel_table_view.horizontalHeader()
        self._channel_table_view.setFixedSize(
            hheader.length()+vheader.width()+2,
            vheader.length()+hheader.height()+2
            )
        self._channel_table_view.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        ### table for Allan deviation results
        self._adev_table_view = QTableView()
        self._adev_table_view.setModel(self._logic.adev_table)
        self._adev_table_view.horizontalHeader().hide()
        self._adev_table_view.verticalHeader().hide()
        self._adev_table_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._adev_table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        vheader = self._adev_table_view.verticalHeader()
        #hheader = self._adev_table_view.horizontalHeader()
        vheader.setSectionResizeMode(QtWidgets.QHeaderView.Fixed) # pylint: disable=locally-disabled, no-member
        vheader.setMaximumSectionSize(row_height)
        self._adev_table_view.resizeRowsToContents()
        self._adev_table_view.resizeColumnsToContents()
        self._adev_table_view.setFixedHeight(vheader.length()+2)
        #self._ch_adev_table_view.setFixedSize(
        #    hheader.length()+vheader.width()+2,
        #    vheader.length()+hheader.height()+2
        #    )
        self._adev_table_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        ### table for evaluation parameters and results
        self._evaluation_table_view = QTableView()
        self._evaluation_table_view.setModel(self._logic.evaluation_table)
        self._evaluation_table_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._evaluation_table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        hheader = self._evaluation_table_view.horizontalHeader()
        hheader.hide()
        vheader = self._evaluation_table_view.verticalHeader()
        vheader.setSectionResizeMode(QtWidgets.QHeaderView.Fixed) # pylint: disable=locally-disabled, no-member
        vheader.setMaximumSectionSize(row_height)
        self._evaluation_table_view.resizeRowsToContents()
        self._evaluation_table_view.setRowHeight(4, 5)
        self._evaluation_table_view.setRowHeight(8, 5)
        self._evaluation_table_view.setRowHeight(11, 5)
        self._evaluation_table_view.setRowHeight(16, 5)
        self._evaluation_table_view.resizeColumnsToContents()
        vheader = self._evaluation_table_view.verticalHeader()
        hheader = self._evaluation_table_view.horizontalHeader()
        self._evaluation_table_view.setMinimumSize(
            hheader.length()+vheader.width()+2,
            vheader.length()+2
            )
        self._evaluation_table_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        ### full size frame to hold the evaluation results
        results_frame = QFrame()
        results_frame.setContentsMargins(0, 0, 0, 0)
        results_frame_layout = QVBoxLayout(results_frame)
        results_frame_layout.addWidget(channel_table_title_label)
        results_frame_layout.addWidget(self._channel_table_view)
        results_frame_layout.addWidget(evaluation_table_title_label)
        results_frame_layout.addWidget(self._evaluation_table_view)
        results_frame_layout.addWidget(ch_adev_table_title_label)
        results_frame_layout.addWidget(self._adev_table_view)

        ### create scrollable area to wrap results frame ###
        scroll_area = QScrollArea()
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        scroll_area.setContentsMargins(0, 0, 0, 0)
        scroll_area.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Minimum)
        scroll_area.setWidget(results_frame)
        width1 = scroll_area.verticalScrollBar().sizeHint().width()
        width2 = results_frame.sizeHint().width()
        scroll_area.setMinimumWidth(width1 + width2)
        # extend width so that vertical bar does not overlap

        #self._freq_box = []
        #for i in range(self._freq_box_number):
        #    self._freq_box.append(FrequencyBox(i))
        #self.mini_log_text = QPlainTextEdit()
        #self.mini_log_text.setReadOnly(True)
        #self.mini_log_text.setMaximumBlockCount(4)
        #metrics = self.mini_log_text.fontMetrics()
        #self.mini_log_text.setFixedHeight(4*metrics.height()+11) #fudge margins
        #self.mini_log_text.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Fixed)
        #self.mini_log_text.setStyleSheet('font: 8pt "Consolas";')
        #self.mini_log_text.setWordWrapMode(QTextOption.NoWrap)

        #self.log_text = QPlainTextEdit()
        #self.log_text.setReadOnly(True)
        #self.log_text.setMaximumBlockCount(100)
        #self.log_text.setStyleSheet('font: 8pt "Consolas";')
        #self.log_text.setWordWrapMode(QTextOption.NoWrap)

        #disp_head_label = QLabel("display settings")
        #disp_head_label.setStyleSheet("font-weight: bold;")
        #self.disp_radio_freq = QRadioButton("frequencies")
        #self.disp_radio_freq.page = 0 # --> corresponds to setting page 0
        #self.disp_radio_freq.toggled.connect(self.disp_radio_toggled)
        #self.disp_radio_raw = QRadioButton("raw readout")
        #self.disp_radio_raw.page = 1 # --> corresponds to setting page 1
        #self.disp_radio_raw.toggled.connect(self.disp_radio_toggled)
        #disp_interval_label = QLabel("measure frequency over:")
        #self._disp_avg_combo = QComboBox()
        #self._disp_avg_combo.addItem("integrate 0.1 s")
        #self._disp_avg_combo.addItem("integrate   3 s")
        #self._disp_avg_combo.setCurrentIndex(-1)
        #self._disp_avg_combo.currentIndexChanged.connect(self.disp_combo_changed)

        #########################################################################
        # overall layout:
        self._graph_widget = QSplitter(Qt.Vertical)
        self._graph_widget.addWidget(graph1)
        self._graph_widget.addWidget(graph2)
        self._graph_widget.setStretchFactor(0, 3)
        self._graph_widget.setStretchFactor(1, 1)

        self._main_widget = QSplitter(Qt.Horizontal)
        self._main_widget.addWidget(scroll_area)
        self._main_widget.addWidget(self._graph_widget)
        self._main_widget.setStretchFactor(0, 0)
        self._main_widget.setStretchFactor(1, 1)
        self.setCentralWidget(self._main_widget)

    def init_state(self):
        """ initialize remaining settings after logic has started """

    def get_graph1_layout(self):
        """return handle for graph 1 window as layout"""
        return self.graph1_layout

    def get_graph2_layout(self):
        """return handle for graph 2 window as layout"""
        return self.graph2_layout

    def set_status(self, text):
        """set normal display text of status bar"""
        self.statusBar().showMessage(text)


    def closeEvent(self, event): # pylint: disable=locally-disabled, invalid-name
        """callback on window close"""
        quit_msg = "Are you sure you want to exit the program?"
        reply = QMessageBox.question(
            self, 'Shutdown',
            quit_msg, QMessageBox.Yes, QMessageBox.No
            )
        if reply == QMessageBox.Yes:
            self._settings.sync()
            event.accept()
        else:
            event.ignore()
            return

        self._settings.setValue('windowposition', self.pos())
        self._settings.setValue('windowsize', self.size())
        self._settings.setValue('basepath', self._base_path)


        #self.settings.setValue('display_size', int(index))
        #labels = []
        #for cnt in range(self._freq_box_number):
        #    labels.append(self._freq_box[cnt].get_label())
        #self.settings.setValue('labels', labels)
        #index = self._size_combo.currentIndex()
        #autosync_state = self._fxe_autosync_check.isChecked()
        #self.settings.setValue('autosync', autosync_state)
        #index = self._fxe_mode_combo.currentIndex()
        #if index >= 0:
        #    self.settings.setValue('fxe_mode', int(index))
        #
        #index = self._disp_avg_combo.currentIndex()
        #self.settings.setValue('integrate_setting', int(index))
        #
        #string = self._labrad_manager_line.text()
        #self.settings.setValue('labrad_manager', string)
        #state = self._store_phase_file_check.isChecked()
        #self.settings.setValue('store_phase', state)
        #state = self._store_freq_file_check.isChecked()
        #self.settings.setValue('store_frequency', state)
        #state = self._store_labrad_check.isChecked()
        #self.settings.setValue('stream_labrad', state)

        #self.logic.shutdown()

        self._settings.setValue('basepath', self._base_path)

def logo():
    """define logo pixmap"""
    logostring = [
        "32 32 4 1", ". c #000000", "G	c #C8C8C8", "O	c #F1C026", "B	c #57BBBB",
        "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGG..",
        "G............................G..",
        "G.OOOOO.OOOO..OOOOO..OOO.....G.G",
        "G.O.....O...O.O.....O...O....GG.",
        "G.OOOO..OOOO..OOOO..O...O....G.G",
        "G.O.....O...O.O.....O..OO....GG.",
        "G.O.....O...O.OOOOO..OOOOO...G.G",
        "G............................GG.",
        "G....OOOOO.O...O..OOO..O.....G.G",
        "G....O.....O...O.O...O.O.....GG.",
        "G....OOOO...O.O..OOOOO.O.....G.G",
        "G.GG.O......O.O..O...O.O.....GG.",
        "G.G..OOOOO...O...O...O.OOOOO.G.G",
        "G.G................G.........GG.",
        "G.GBBB.............G.........G.G",
        "G.GOOBBB...........G.GG.GGGG.GG.",
        "G.GO.OBBBG.G.G.G.G.G.........G.G",
        "G.G.O.OBBB.........G.GGGGG.G.GG.",
        "G.GO.O.OBB.........G.........G.G",
        "G.G.O.O.OBB........G.GGGGGGG.GG.",
        "G.GO.O.O.OBB.......G.........G.G",
        "G.G.O.O.O.OBBB.G.G.G.G.GGG.G.GG.",
        "G.GO.O.O.O.OBBBB...G.........G.G",
        "G.G.O.O.O.O.OBBBB..G.GG.GGGG.GG.",
        "G.GO.O.O.O.O.OBBBB.G.........G.G",
        "G.G.O.O.O.O.O.OBBBBG.GGGG.GG.GG.",
        "G.GO.O.O.O.O.O.OBBBG.........G.G",
        "G.GGGGGGGGGGGGGGGGGG.G.GGGGG.GG.",
        "G............................G.G",
        "GGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG.",
        "...G.G.G.G.G.G.G.G.G.G.G.G.G.G.G",
        "..G.G.G.G.G.G.G.G.G.G.G.G.G.G.G."]
    return logostring


if __name__ == '__main__':
    #app = QApplication(sys.argv)  # pylint: disable=locally-disabled, invalid-name
    #frame = FreqEvalMain()  # pylint: disable=locally-disabled, invalid-name
    #sys.exit(app.exec_())
    pass

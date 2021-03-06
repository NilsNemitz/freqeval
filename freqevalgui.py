#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Main GUI code for frequency evaluation program
Created on 2017/09/03
@author: Nils Nemitz
"""

# py#lint: disable=locally-disabled, redefined-variable-type
# pylint: disable=locally-disabled, too-many-instance-attributes

import os

from PyQt5 import ( # pylint: disable=locally-disabled, no-name-in-module
    QtGui, QtCore, QtWidgets
    )
from PyQt5.QtWidgets import ( # pylint: disable=locally-disabled, no-name-in-module
    QMainWindow, QMessageBox,
    #QApplication, QWidget, #QPlainTextEdit,
    QFrame, QLabel, QTableView, QHeaderView, #QTableWidget, QTableWidgetItem,
    QFileDialog, QPushButton, QComboBox,
    QAction,
    #QHBoxLayout,
    QVBoxLayout,
    QGridLayout,
    #QSpacerItem,
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
        self._init_gui()
        self._logic.init_graphs()
        self.show()
        self.init_state() # code in init_state has access to logic already
        self._base_path = self._settings.value('basepath', "")

    ###############################################################################
    def show_msg(self, title, text):
        """ show dialog with message, to be called from subroutines """
        QMessageBox.about(self, title, text)

    def confirm_msg(self, text):
        """ show dialog with message, to be called from subroutines """
        reply = QMessageBox.question(
            self, 'Confirm',
            text, QMessageBox.Yes, QMessageBox.No
            )
        if reply == QMessageBox.Yes:
            return True
        else:
            return False

    ###############################################################################
    def show_msg_not_implemented(self, qval):
        """ show dialog indicating not-yet-implemented feature, called directly from menus """
        del qval
        self.show_msg("Not implemented", "This function is not yet implemented.")

    ###############################################################################
    def redraw(self, qval):
        """ manually trigger window redraw """
        del qval
        print("forced redraw")
        self._channel_table.update()
        self._evaluation_table_view.update()
        self._adev_table_view.update()
        self._main_widget.update()
        #self._channel_table_view.refresh()
        #self._graph_widget.refresh()
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
    def _init_gui(self):
        """initialize and load basic settings for UI"""
        self.setWindowTitle('Frequency Evaluation for Comb Count')
        self.resize(self._settings.value('windowsize', QtCore.QSize(270, 225))) # pylint: disable=locally-disabled, no-member
        self.move(self._settings.value('windowposition', QtCore.QPoint(50, 50))) # pylint: disable=locally-disabled, no-member

        row_height = 24

        ### set up menus #########################################################
        menubar = self.menuBar()

        open_act = QAction('&Open', self)
        open_act.setShortcut('Ctrl+O')
        open_act.setStatusTip('Open data file')
        open_act.triggered.connect(self.select_data_file)

        savemask_act = QAction('Save &mask data', self)
        #savemask_act.setShortcut('Ctrl+R')
        savemask_act.setStatusTip('Save mask information for current data set')
        savemask_act.triggered.connect(self._logic.save_maskfile_passthru)

        report_act = QAction('&Generate report', self)
        report_act.setShortcut('Ctrl+G')
        report_act.setStatusTip('Generate report and save config for current data file')
        report_act.triggered.connect(self._logic.save_report_passthru)

        save_config_act = QAction('Save &default config', self)
        #save_config_act.setShortcut('Ctrl+O')
        save_config_act.setStatusTip('Save current channel and evaluation configuration as default')
        save_config_act.triggered.connect(self._logic.save_default_config_passthru)

        exit_act = QAction('&Exit', self)
        exit_act.setShortcut('Ctrl+Q')
        exit_act.setStatusTip('Exit application')
        exit_act.triggered.connect(self.close)

        file_menu = menubar.addMenu('&File')
        file_menu.addAction(open_act)
        file_menu.addAction(savemask_act)
        file_menu.addAction(report_act)
        file_menu.addAction(save_config_act)
        file_menu.addAction(exit_act)

        mask_act = QAction('&Mask selected', self)
        mask_act.setShortcut('Ctrl+M')
        mask_act.setStatusTip('Mask data between selected points')
        mask_act.triggered.connect(self._logic.mask_selected_passthru)

        edit_mask_act = QAction('((&Edit masks))', self)
        edit_mask_act.setStatusTip('Edit list of applied masks')
        edit_mask_act.setChecked(True)
        edit_mask_act.triggered.connect(self.show_msg_not_implemented)

        mask_menu = menubar.addMenu('&Mask')
        mask_menu.addAction(mask_act)
        mask_menu.addAction(edit_mask_act)

        view_all_act = QAction('View &all', self)
        view_all_act.setShortcut('Ctrl+A')
        view_all_act.setStatusTip('View all data')
        view_all_act.triggered.connect(self._logic.zoom_all)

        zoom_good_act = QAction('&Zoom good data', self)
        zoom_good_act.setShortcut('Ctrl+Z')
        zoom_good_act.setStatusTip('Zoom in to show only good data')
        zoom_good_act.triggered.connect(self._logic.zoom_good)

        view1_act = QAction('View &1: Channels', self)
        view1_act.setShortcut('Ctrl+1')
        view1_act.setStatusTip('Arrange graphs for inspection of single channel data')
        view1_act.triggered.connect(self.arrange_channels)

        view2_act = QAction('View &2: Evaluation', self)
        view2_act.setShortcut('Ctrl+2')
        view2_act.setStatusTip('Arrange graphs for inspection of evaluation data')
        view2_act.triggered.connect(self.arrange_evaluations)

        view3_act = QAction('View &3: Results', self)
        view3_act.setShortcut('Ctrl+3')
        view3_act.setStatusTip('Arrange graphs to give an overview of results')
        view3_act.triggered.connect(self.arrange_results)

        redraw_act = QAction('&Redraw', self)
        redraw_act.setShortcut('Ctrl+R')
        redraw_act.setStatusTip('Redraw window')
        redraw_act.triggered.connect(self.redraw)

        mask_menu = menubar.addMenu('&View')
        mask_menu.addAction(view_all_act)
        mask_menu.addAction(zoom_good_act)
        mask_menu.addAction(view1_act)
        mask_menu.addAction(view2_act)
        mask_menu.addAction(view3_act)        
        mask_menu.addAction(redraw_act)

        self.file_info_label = QLabel('filename/filename/filename.fil : MJD 12345')
        self.statusBar().addPermanentWidget(self.file_info_label)

        ### sub-frame for time series graphs (upper region) ###
        self.graph1_layout = pg.GraphicsLayout()
        self.graph1_layout.setSpacing(0.)
        self.graph1_layout.setContentsMargins(0., 1., 0., 1.)
        graph1 = pg.GraphicsView()
        graph1.setCentralItem(self.graph1_layout)

        ### sub-frame for evaluation time series graph (bottom region) ###
        self.graph2_layout = pg.GraphicsLayout()
        self.graph2_layout.setSpacing(0.)
        self.graph2_layout.setContentsMargins(0., 10., 0., 0.)
        graph2 = pg.GraphicsView()
        graph2.setCentralItem(self.graph2_layout)

        ### sub-frame for ADev graphs (middle column) ###
        self.graph3_layout = pg.GraphicsLayout()
        self.graph3_layout.setSpacing(0.)
        self.graph3_layout.setContentsMargins(0., 10., 0., 0.)
        self._adev_graph_widget = pg.GraphicsView()
        self._adev_graph_widget.setCentralItem(self.graph3_layout)        

        ### subframe (in scrollpanel?) for masking controls / selection readout
        mask_title_label = QLabel("Data selection")
        mask_title_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        mask_title_label.setStyleSheet("font-weight: bold;")
        mask_table = QTableView()
        mask_table.setModel(self._logic.selection_table)
        mask_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        mask_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        vheader = mask_table.verticalHeader()
        hheader = mask_table.horizontalHeader()
        vheader.setSectionResizeMode(QtWidgets.QHeaderView.Fixed) # pylint: disable=locally-disabled, no-member
        hheader.setSectionResizeMode(QtWidgets.QHeaderView.Fixed) # pylint: disable=locally-disabled, no-member
        vheader.setMaximumSectionSize(row_height)
        mask_table.resizeRowsToContents()
        mask_table.resizeColumnsToContents()
        mask_table.setFixedSize(
            hheader.length()+vheader.sizeHint().width()+2,
            vheader.length()+hheader.sizeHint().height()+2
            )
        mask_table.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        mask_button = QPushButton('Mask selected')
        mask_button.clicked.connect(self._logic.mask_selected_passthru)

        self._mask_channel_box = QComboBox()
        self._mask_channel_box.addItem('ch 1', 0b00000001)
        self._mask_channel_box.addItem('ch 2', 0b00000010)
        self._mask_channel_box.addItem('ch 3', 0b00000100)
        self._mask_channel_box.addItem('ch 4', 0b00001000)
        self._mask_channel_box.addItem( 'all', 0b11111111)
        self._mask_channel_box.setCurrentIndex(4)

        view_label = QLabel("Quick view")
        view_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)        
        view_label.setStyleSheet("font-weight: bold;")
        view_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        view_button1 = QPushButton('1: channels')
        view_button1.setStyleSheet("text-align: left;")
        view_button1.clicked.connect(self.arrange_channels)
        view_button2 = QPushButton('2: evaluation')
        view_button2.setStyleSheet("text-align: left;")
        view_button2.clicked.connect(self.arrange_evaluations)
        view_button3 = QPushButton('3: results')
        view_button3.setStyleSheet("text-align: left;")
        view_button3.clicked.connect(self.arrange_results)
        spacer = QLabel('')
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        mask_frame = QFrame()
        mask_frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        mask_frame_layout = QGridLayout(mask_frame)
        mask_frame_layout.setVerticalSpacing(2)
        mask_frame_layout.setContentsMargins(0, 0, 0, 0)
        mask_frame_layout.addWidget(mask_title_label, 0, 0, 1, 1)
        mask_frame_layout.addWidget(self._mask_channel_box, 2, 0, 1, 1)
        mask_frame_layout.addWidget(mask_button, 3, 0, 1, 1)
        mask_frame_layout.addWidget(mask_table, 0, 1, 4, 1)
        mask_frame_layout.addWidget(spacer, 0, 2, 1, 1)
        mask_frame_layout.addWidget(view_label, 0, 3, 1, 1)
        mask_frame_layout.addWidget(view_button1, 1, 3, 1, 1)
        mask_frame_layout.addWidget(view_button2, 2, 3, 1, 1)
        mask_frame_layout.addWidget(view_button3, 3, 3, 1, 1)
        
        ### scrollable sub-frame for results and configuration tables
        hor_spacer = QFrame()
        hor_spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        channel_table_title_label = QLabel("Channel settings")
        channel_table_title_label.setStyleSheet("font-weight: bold;")
        ch_adev_table_title_label = QLabel("Instabilities (overlapping Allan deviation)")
        ch_adev_table_title_label.setStyleSheet("font-weight: bold;")
        evaluation_table_title_label = QLabel("Evaluation settings and results")
        evaluation_table_title_label.setStyleSheet("font-weight: bold;")

        ### table for channel parameters
        self._channel_table = QTableView()
        self._channel_table.setModel(self._logic.channel_table)
        self._channel_table.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._channel_table.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        vertical_header = self._channel_table.verticalHeader()
        vertical_header.setSectionResizeMode(QtWidgets.QHeaderView.Fixed) # pylint: disable=locally-disabled, no-member
        vertical_header.setMaximumSectionSize(row_height)
        self._channel_table.resizeRowsToContents()
        self._channel_table.resizeColumnsToContents()
        vheader = self._channel_table.verticalHeader()
        hheader = self._channel_table.horizontalHeader()
        self._channel_table.setFixedSize(
            hheader.length()+vheader.width()+2,
            vheader.length()+hheader.height()+2
            )
        self._channel_table.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        ### table for Allan deviation results
        self._adev_table_view = QTableView()
        self._adev_table_view.setModel(self._logic.adev_table)
        self._adev_table_view.horizontalHeader().hide()
        # self._adev_table_view.verticalHeader().hide()
        self._adev_table_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._adev_table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        vheader = self._adev_table_view.verticalHeader()
        vheader.setSectionResizeMode(QtWidgets.QHeaderView.Fixed) # pylint: disable=locally-disabled, no-member
        vheader.setMaximumSectionSize(row_height)
        hheader = self._adev_table_view.horizontalHeader()
        hheader.setSectionResizeMode(QHeaderView.Stretch)

        self._adev_table_view.resizeRowsToContents()
        self._adev_table_view.resizeColumnsToContents()
        self._adev_table_view.setFixedHeight(vheader.length()+2)
        self._adev_table_view.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        ### table for evaluation parameters and results
        self._evaluation_table_view = QTableView()
        self._evaluation_table_view.setModel(self._logic.evaluation_table)
        self._evaluation_table_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._evaluation_table_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        hheader = self._evaluation_table_view.horizontalHeader()
        hheader.hide()
        hheader.setSectionResizeMode(QHeaderView.Stretch)
        vheader = self._evaluation_table_view.verticalHeader()
        vheader.setSectionResizeMode(QtWidgets.QHeaderView.Fixed) # pylint: disable=locally-disabled, no-member
        vheader.setMaximumSectionSize(row_height)
        self._evaluation_table_view.resizeRowsToContents()
        for divider_row in (5, 9, 14, 19):
            self._evaluation_table_view.setRowHeight(divider_row, 5)
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
        
        results_frame_layout.addWidget(mask_frame)
        results_frame_layout.addWidget(channel_table_title_label)
        results_frame_layout.addWidget(self._channel_table)
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

        #########################################################################
        # overall layout:
        self._time_graph_widget = QSplitter(Qt.Vertical)
        self._time_graph_widget.addWidget(graph1)
        self._time_graph_widget.addWidget(graph2)
        self._time_graph_widget.setStretchFactor(0, 3)
        self._time_graph_widget.setStretchFactor(1, 1)

        self._main_widget = QSplitter(Qt.Horizontal)
        self._main_widget.addWidget(self._time_graph_widget)
        self._main_widget.addWidget(self._adev_graph_widget)
        self._main_widget.addWidget(scroll_area)
        self._main_widget.setStretchFactor(0, 3)
        self._main_widget.setStretchFactor(1, 1)
        self._main_widget.setStretchFactor(2, 0)
        self.setCentralWidget(self._main_widget)

    def init_state(self):
        """ initialize remaining settings after logic has started """

    def get_mask_flags(self):
        index = int(self._mask_channel_box.currentIndex())
        flags = self._mask_channel_box.itemData(index) & 0xFF
        return flags

    def set_status(self, text):
        """set normal display text of status bar"""
        self.statusBar().showMessage(text)

    def set_file_info(self, text):
        """set file information text in status bar"""
        self.file_info_label.setText(text)

    ###############################################################################################
    def arrange_channels(self, qval):
        """ quick-arrange splitters to suitable settings for channal data """
        del qval
        print('[arrange_channels] Arranging windows for channel mode')
        sizes = self._time_graph_widget.sizes()
        graph_height = sizes[0] + sizes[1]
        sizes[0] = graph_height
        sizes[1] = 0
        self._time_graph_widget.setSizes(sizes)
        sizes = self._main_widget.sizes()
        graph_width = sizes[0] + sizes[1]
        sizes[0] = graph_width
        sizes[1] = 0
        self._main_widget.setSizes(sizes)
        self._logic.zoom_all(None)

    ###############################################################################################
    def arrange_evaluations(self, qval):
        """ quick-arrange splitters to suitable settings for evaluations """
        del qval
        sizes = self._time_graph_widget.sizes()
        graph_height = sizes[0] + sizes[1]
        sizes[0] = int(0.3 * graph_height)
        sizes[1] = graph_height - sizes[0]
        self._time_graph_widget.setSizes(sizes)
        sizes = self._main_widget.sizes()
        graph_width = sizes[0] + sizes[1]
        sizes[0] = int(0.8 * graph_width)
        sizes[1] = graph_width - sizes[0]
        self._main_widget.setSizes(sizes)
        self._logic.zoom_good(None)

    ###############################################################################################
    def arrange_results(self, qval):
        """ quick-arrange splitters to suitable settings for overview of results """
        del qval
        sizes = self._time_graph_widget.sizes()
        graph_height = sizes[0] + sizes[1]
        sizes[0] = int(0.45 * graph_height)
        sizes[1] = graph_height - sizes[0]
        self._time_graph_widget.setSizes(sizes)
        sizes = self._main_widget.sizes()
        graph_width = sizes[0] + sizes[1]
        sizes[0] = int(0.6 * graph_width)
        sizes[1] = graph_width - sizes[0]
        self._main_widget.setSizes(sizes)
        self._logic.zoom_good(None)

    ###############################################################################################
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
        #self.logic.shutdown()

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

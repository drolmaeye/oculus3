__author__ = 'jssmith'

'''
A GUI for displaying 1D scans collected using the EPICS scan record
'''

# import necessary modules
import sys
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg
import pyqtgraph as pg
import numpy as np
from epics import PV
import time
import os


class MainWindow(qtw.QMainWindow):
    update_plot_signal = qtc.pyqtSignal(bool)

    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1080, 720)
        self.setWindowTitle('Oculus Machina development version')
        self.setWindowIcon(qtg.QIcon('eye1.png'))

        # create main window widget and make it the central widget
        self.main_window = qtw.QWidget()
        self.setCentralWidget(self.main_window)
        # make the outermost layout for the main window
        self.main_window_layout = qtw.QVBoxLayout()
        self.main_window.setLayout(self.main_window_layout)

        '''
        Menu bar
        '''

        '''
        Custom Toolbar
        '''

        '''
        Plot Window
        '''
        # make plot window for upper-left (largest) potion of main window
        self.plot_window = pg.PlotWidget(name='Plot1')
        # self.plot_window.addLegend()
        # custom viewbox, vb, allows for custom button event handling, placeholder here in case
        # self.plot_window = pg.PlotWidget(viewBox=vb, name='Plot1')

        # prepare to generate line style list for up to 70 detectors
        color_list = [
            (0, 0, 200),
            (0, 128, 0),
            (19, 234, 201),
            (195, 46, 212),
            (250, 194, 5),
            (0, 114, 189),
            (217, 83, 25),
            (237, 177, 32),
            (126, 47, 142),
            (119, 172, 48)]

        symbol_list = [
            'o',
            't1',
            's',
            'd',
            'star',
            't',
            '+']

        symbol_pen = 'w'
        symbol_size = 4
        width = 2

        # generate line style list for up to 70 detectors
        line_style_list = []
        for i in symbol_list:
            for j in color_list:
                keywords = {'pen': {'color': j, 'width': width}, 'symbolBrush': j, 'symbolPen': j, 'symbol': i, 'symbolSize': symbol_size}
                line_style_list.append(keywords)

        # create a dictionary of the line/symbol display for each detector
        self.dnncv_line_symbol = {}
        # TODO get back to NUM_DETECTORS below
        # for i in range(1, scan1.NUM_DETECTORS + 1):
        for i in range(1, 30 + 1):
            key_dnncv_ls = 'D%2.2iCV' % i
            self.dnncv_line_symbol[key_dnncv_ls] = pg.PlotDataItem(name=key_dnncv_ls, **line_style_list[i - 1])

        # create, add, and connect movable vertical and horizontal lines
        self.vline_min = pg.InfiniteLine(pos=-0.3, angle=90, pen='b', movable=True)
        self.vline_mid = pg.InfiniteLine(pos=0.0, angle=90, pen={'color': 'r', 'style': qtc.Qt.DashLine}, movable=False)
        self.vline_max = pg.InfiniteLine(pos=0.3, angle=90, pen='b', movable=True)
        self.hline_min = pg.InfiniteLine(pos=-0.3, angle=0, pen='b', movable=True)
        self.hline_mid = pg.InfiniteLine(pos=0.0, angle=0, pen={'color': 'r', 'style': qtc.Qt.DashLine}, movable=False)
        self.hline_max = pg.InfiniteLine(pos=0.3, angle=0, pen='b', movable=True)

        self.plot_window.addItem(self.vline_min)
        self.plot_window.addItem(self.vline_mid)
        self.plot_window.addItem(self.vline_max)
        self.plot_window.addItem(self.hline_min)
        self.plot_window.addItem(self.hline_mid)
        self.plot_window.addItem(self.hline_max)

        self.vline_min.sigPositionChanged.connect(self.vline_moved)
        self.vline_max.sigPositionChanged.connect(self.vline_moved)
        self.hline_min.sigPositionChanged.connect(self.hline_moved)
        self.hline_max.sigPositionChanged.connect(self.hline_moved)

        '''
        Control area
        '''

        # make the control window container widget
        self.control_window = qtw.QWidget()
        self.control_window_layout = qtw.QHBoxLayout()
        self.control_window.setLayout(self.control_window_layout)

        '''
        Detectors window
        '''

        # make widget for detectors window
        self.detectors_window = qtw.QGroupBox()
        self.detectors_window.setTitle('Detectors')
        self.control_window_layout.addWidget(self.detectors_window)

        # make and set layout for detectors window
        self.detectors_window_layout = qtw.QVBoxLayout()
        self.detectors_window.setLayout(self.detectors_window_layout)

        # ###make individual widgets for detector selection window###

        # ###make the container widget for position and file selectors###
        self.container_widget = qtw.QWidget()
        self.container_widget_layout = qtw.QVBoxLayout()
        self.container_widget.setLayout(self.container_widget_layout)

        '''
        Position window
        '''

        # make widget for position widget
        self.position_window = qtw.QGroupBox()
        self.position_window.setTitle('Positions')
        self.container_widget_layout.addWidget



        





        self.show()

    def vline_moved(self):
        min = self.vline_min.getXPos()
        max = self.vline_max.getXPos()
        print(min, max)
        mid = (min + max) / 2.0
        self.vline_mid.setX(mid)

    def hline_moved(self):
        min = self.hline_min.getYPos()
        max = self.hline_max.getYPos()
        print(min, max)
        mid = (min + max) / 2.0
        self.hline_mid.setY(mid)




if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    root, stump = '16test:', 'scan1.'
    w = MainWindow()
    sys.exit(app.exec_())

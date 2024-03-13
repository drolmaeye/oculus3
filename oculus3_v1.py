__author__ = 'jssmith'

'''
A GUI for displaying 1D scans collected using the EPICS scan record
'''

'''
restart project March 2024
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
        # ###Layout management###
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
        # make plot window for upper potion of main window
        self.plot_window = pg.PlotWidget(name='Plot1')#, background='w')
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

        # symbol_pen = 'w'
        symbol_size = 4
        width = 2

        # generate line style list for up to 70 detectors
        line_style_list = []
        for i in symbol_list:
            for j in color_list:
                keywords = {
                    'pen': {'color': j, 'width': width},
                    'symbolBrush': j, 'symbolPen': j,
                    'symbol': i,
                    'symbolSize': symbol_size}
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

        # ###Layout management###
        # add plot window to main window layout
        self.main_window_layout.addWidget(self.plot_window)

        '''
        Control area
        '''

        # ###Layout management###
        # make the control window container widget
        self.control_window = qtw.QWidget()
        self.control_window_layout = qtw.QHBoxLayout()
        self.control_window.setLayout(self.control_window_layout)
        self.main_window_layout.addWidget(self.control_window)

        # make the three container widgets for the control window
        self.control_window_left = qtw.QWidget()
        self.control_window_left_layout = qtw.QVBoxLayout()
        self.control_window_left.setLayout(self.control_window_left_layout)
        self.control_window_layout.addWidget(self.control_window_left)

        self.control_window_center = qtw.QWidget()
        self.control_window_center_layout = qtw.QVBoxLayout()
        self.control_window_center.setLayout(self.control_window_center_layout)
        self.control_window_layout.addWidget(self.control_window_center)

        self.control_window_right = qtw.QWidget()
        self.control_window_right_layout = qtw.QVBoxLayout()
        self.control_window_right.setLayout(self.control_window_right_layout)
        self.control_window_layout.addWidget(self.control_window_right)

        '''
        Detectors window
        '''

        # make widget for detectors window
        self.detectors_window = qtw.QGroupBox(title='Detectors')
        # self.detectors_window.setTitle('Detectors')
        self.detectors_window_layout = qtw.QVBoxLayout()
        self.detectors_window.setLayout(self.detectors_window_layout)
        self.control_window_left_layout.addWidget(self.detectors_window)

        '''
        Position window
        '''

        # make position window widget
        self.position_window = qtw.QGroupBox()
        self.position_window.setTitle('Positions')
        self.position_window_layout = qtw.QVBoxLayout()
        self.position_window.setLayout(self.position_window_layout)
        self.control_window_center_layout.addWidget(self.position_window)

        '''
        File window
        '''
        # make file window widget
        self.file_window = qtw.QGroupBox()
        self.file_window.setTitle('File')
        self.file_window_layout = qtw.QVBoxLayout()
        self.file_window.setLayout(self.file_window_layout)
        self.control_window_center_layout.addWidget(self.file_window)

        '''
        Buttons window
        '''
        self.buttons_window = qtw.QGroupBox()
        self.buttons_window.setTitle('buttons')
        self.buttons_window_layout = qtw.QVBoxLayout()
        self.buttons_window.setLayout(self.buttons_window_layout)
        self.control_window_right_layout.addWidget(self.buttons_window)

        self.show()

    def vline_moved(self):
        v_min = self.vline_min.getXPos()
        v_max = self.vline_max.getXPos()
        print(v_min, v_max)
        v_mid = (v_min + v_max) / 2.0
        self.vline_mid.setX(v_mid)

    def hline_moved(self):
        h_min = self.hline_min.getYPos()
        h_max = self.hline_max.getYPos()
        print(h_min, h_max)
        h_mid = (h_min + h_max) / 2.0
        self.hline_mid.setY(h_mid)


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    root, stump = '16test:', 'scan1.'
    w = MainWindow()
    sys.exit(app.exec_())

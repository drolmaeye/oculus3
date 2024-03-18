import sys
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg
import pyqtgraph as pg
import numpy as np
from epics import PV, caget
from epics.devices import Scan
import time
import os


class MainWindow(qtw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1080, 720)
        self.setWindowTitle('Oculus')
        self.setWindowIcon(qtg.QIcon('eye1.png'))
        self.setStyleSheet('font-size: 10pt')

        # create central widget
        self.main_widget = qtw.QWidget()
        self.setCentralWidget(self.main_widget)
        self.main_layout = qtw.QHBoxLayout()
        self.main_widget.setLayout(self.main_layout)

        # establish left and right sides of GUI
        self.left_side_layout = qtw.QVBoxLayout()
        self.main_layout.addLayout(self.left_side_layout)
        self.right_side_layout = qtw.QVBoxLayout()
        self.main_layout.addLayout(self.right_side_layout)

        '''Menu bar'''

        # actions
        self.close_oculus_action = qtw.QAction('Exit', self)
        self.close_oculus_action.setShortcut('Ctrl+Q')

        # make menu, add headings, add actions
        self.main_menu = self.menuBar()
        self.file_menu = self.main_menu.addMenu('File')
        self.file_menu.addAction(self.close_oculus_action)

        '''
        Left side
        '''

        '''Plot window'''

        self.plot_window = pg.PlotWidget(name='plot1')
        self.left_side_layout.addWidget(self.plot_window)

        # generate line and symbol lists for plot data items
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

        line_style_list = []
        for i in symbol_list:
            for j in color_list:
                keywords = {'pen': {'color': j, 'width': width}, 'symbolBrush': j, 'symbolPen': j, 'symbol': i, 'symbolSize': symbol_size}
                line_style_list.append(keywords)
        # print(line_style_list)

        self.dnncv = {}
        # for i in range(1, scan1.NUM_DETECTORS + 1):
        for i in range(1, 31):
            key_cv = 'D%2.2iCV' % i
            self.dnncv[key_cv] = pg.PlotDataItem(name=key_cv, **line_style_list[i - 1])
            self.plot_window.addItem(self.dnncv[key_cv])


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
        Right side
        '''

        '''File control'''

        # create file control groupbox and add to the right side layout
        self.file_control = qtw.QGroupBox()
        self.file_control.setTitle('File Control')
        self.file_control_layout = qtw.QHBoxLayout()
        self.file_control.setLayout(self.file_control_layout)
        self.right_side_layout.addWidget(self.file_control)

        # create file control widgets
        self.current_file_label = qtw.QLabel('Current scan file')
        self.current_file_ledit = qtw.QLineEdit()
        self.current_file_decrement = qtw.QPushButton('<')
        self.current_file_increment = qtw.QPushButton('>')
        self.load_file_button = qtw.QPushButton('Load data')
        self.save_file_button = qtw.QPushButton('Save ASCII')

        # add file control widgets to the file control groupbox
        self.file_control_layout.addWidget(self.current_file_label)
        self.file_control_layout.addWidget(self.current_file_ledit)
        self.file_control_layout.addWidget(self.current_file_decrement)
        self.file_control_layout.addWidget(self.current_file_increment)
        self.file_control_layout.addWidget(self.load_file_button)
        self.file_control_layout.addWidget(self.save_file_button)

        '''Markers control'''

        self.markers_control = qtw.QGroupBox()
        self.markers_control.setTitle('Markers Control')
        self.markers_control_layout = qtw.QHBoxLayout()
        self.markers_control.setLayout(self.markers_control_layout)
        self.right_side_layout.addWidget(self.markers_control)

        # create markers control widgets
        self.reset_markers_label = qtw.QLabel('Reset markers')
        self.reset_vertical_markers_button = qtw.QPushButton('Vertical')
        self.reset_horizontal_markers_button = qtw.QPushButton('Horizontal')
        self.reset_all_markers_button = qtw.QPushButton('All')
        self.position_difference_label = qtw.QLabel('Difference')
        self.position_difference_ledit = qtw.QLineEdit()

        # add plot toolbar widgets to plot toolbar layout
        self.markers_control_layout.addWidget(self.reset_markers_label)
        self.markers_control_layout.addWidget(self.reset_vertical_markers_button)
        self.markers_control_layout.addWidget(self.reset_horizontal_markers_button)
        self.markers_control_layout.addWidget(self.reset_all_markers_button)
        self.markers_control_layout.addWidget(self.position_difference_label)
        self.markers_control_layout.addWidget(self.position_difference_ledit)

        '''Position control'''

        # create position control groupbox and add to the right side layout
        self.position_control = qtw.QGroupBox()
        self.position_control.setTitle('Position Control')
        self.position_control_layout = qtw.QGridLayout()
        self.position_control.setLayout(self.position_control_layout)
        self.right_side_layout.addWidget(self.position_control)

        # create position control widgets
        self.active_element_label = qtw.QLabel('Active element')
        self.minimum_position_label = qtw.QLabel('Minimum')
        self.center_position_label = qtw.QLabel('Center')
        self.maximum_position_label = qtw.QLabel('Maximum')
        self.width_label = qtw.QLabel('Width')

        self.horizontal_axis_label = qtw.QLabel('Horizontal axis')
        self.active_horizontal_axis_combo = qtw.QComboBox()
        self.active_horizontal_axis_combo.addItem('Positioners')
        self.hax_vline_min_position_button = qtw.QPushButton('')
        self.hax_vline_mid_position_button = qtw.QPushButton('')
        self.hax_vline_max_position_button = qtw.QPushButton('')
        self.hax_vline_markers_width = qtw.QLineEdit()

        self.vertical_axis_label = qtw.QLabel('Vertical axis')
        self.active_vertical_axis_combo = qtw.QComboBox()
        self.active_vertical_axis_combo.addItem('Detectors')
        self.vax_hline_min_position_button = qtw.QPushButton('')
        self.vax_hline_mid_position_button = qtw.QPushButton('')
        self.vax_hline_max_position_button = qtw.QPushButton('')
        self.vax_hline_markers_width = qtw.QLineEdit()

        # add position control widgets to position control groupbox
        self.position_control_layout.addWidget(self.active_element_label, 0, 1, 1, 2)
        self.position_control_layout.addWidget(self.minimum_position_label, 0, 3)
        self.position_control_layout.addWidget(self.center_position_label, 0, 4)
        self.position_control_layout.addWidget(self.maximum_position_label, 0, 5)
        self.position_control_layout.addWidget(self.width_label, 0, 6)

        self.position_control_layout.addWidget(self.horizontal_axis_label, 1, 0)
        self.position_control_layout.addWidget(self.active_horizontal_axis_combo, 1, 1, 1, 2)
        self.position_control_layout.addWidget(self.hax_vline_min_position_button, 1, 3)
        self.position_control_layout.addWidget(self.hax_vline_mid_position_button, 1, 4)
        self.position_control_layout.addWidget(self.hax_vline_max_position_button, 1, 5)
        self.position_control_layout.addWidget(self.hax_vline_markers_width, 1, 6)

        self.position_control_layout.addWidget(self.vertical_axis_label, 2, 0)
        self.position_control_layout.addWidget(self.active_vertical_axis_combo, 2, 1, 1, 2)
        self.position_control_layout.addWidget(self.vax_hline_min_position_button, 2, 3)
        self.position_control_layout.addWidget(self.vax_hline_mid_position_button, 2, 4)
        self.position_control_layout.addWidget(self.vax_hline_max_position_button, 2, 5)
        self.position_control_layout.addWidget(self.vax_hline_markers_width, 2, 6)

        '''
        Detectors Window
        '''

        # create position control groupbox and add to the right side layout
        self.detectors_control = qtw.QGroupBox()
        self.detectors_control.setTitle('Detectors Control')
        self.detectors_control_layout = qtw.QGridLayout()
        self.detectors_control.setLayout(self.detectors_control_layout)
        self.right_side_layout.addWidget(self.detectors_control)

        self.dnncb = {}
        for i in range(10):
            for j in range(3):
                number = j * 10 + 1 + i
                key_cb = 'D%2.2iCB' % number
                self.dnncb[key_cb] = qtw.QCheckBox(str(number))
                self.dnncb[key_cb].stateChanged.connect(self.det_cbox_toggled)
                self.detectors_control_layout.addWidget(self.dnncb[key_cb], i, j)

        '''Windows control'''

        # create windows control groupbox and add to right side layout
        self.windows_control = qtw.QGroupBox()
        self.windows_control.setTitle('Windows Control')
        self.windows_control_layout = qtw.QHBoxLayout()
        self.windows_control.setLayout(self.windows_control_layout)
        self.right_side_layout.addWidget(self.windows_control)

        # create windows control widgets
        self.overlays_button = qtw.QPushButton('Overlays')
        self.abort_button = qtw.QPushButton('Abort')
        self.quit_button = qtw.QPushButton('Quit')

        # add windows control widgets to windows control groupbox
        self.windows_control_layout.addWidget(self.overlays_button)
        self.windows_control_layout.addWidget(self.abort_button)
        self.windows_control_layout.addWidget(self.quit_button)

    def vline_moved(self):
        v_min = self.vline_min.getXPos()
        v_max = self.vline_max.getXPos()
        v_mid = (v_min + v_max) / 2.0
        v_width = v_max - v_min
        self.vline_mid.setX(v_mid)
        self.hax_vline_min_position_button.setText('%.3f' % v_min)
        self.hax_vline_mid_position_button.setText('%.3f' % v_mid)
        self.hax_vline_max_position_button.setText('%.3f' % v_max)
        self.hax_vline_markers_width.setText('%.4f' % v_width)

    def hline_moved(self):
        h_min = self.hline_min.getYPos()
        h_max = self.hline_max.getYPos()
        h_mid = (h_min + h_max) / 2.0
        h_width = h_max - h_min
        self.hline_mid.setY(h_mid)
        self.vax_hline_min_position_button.setText('%.3f' % h_min)
        self.vax_hline_mid_position_button.setText('%.3f' % h_mid)
        self.vax_hline_max_position_button.setText('%.3f' % h_max)
        self.vax_hline_markers_width.setText('%.4f' % h_width)

    def det_cbox_toggled(self):
        item_list = self.plot_window.listDataItems()
        for key_cb in self.dnncb:
            key_cv = key_cb.replace('B', 'V')
            if self.dnncb[key_cb].isChecked() and self.dnncv[key_cv] not in item_list:
                self.plot_window.addItem(self.dnncv[key_cv])
            elif not self.dnncb[key_cb].isChecked() and self.dnncv[key_cv] in item_list:
                self.plot_window.removeItem(self.dnncv[key_cv])
        print(self.plot_window.listDataItems())










if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    gui = MainWindow()
    gui.show()
    sys.exit(app.exec_())

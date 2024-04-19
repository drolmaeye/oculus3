import sys
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg
import pyqtgraph as pg
import constants
import numpy as np
from epics import PV, caget
from epics.devices import Scan
import time
import os
from pyqtgraph.graphicsItems.LegendItem import ItemSample
from detector_checkbox import Window


class PyQtView(qtw.QMainWindow):
    def __init__(self, controller):
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
        y_axis_label = 'Counts'
        label_style = {'color': '#808080', 'font': ' bold 16px'}
        self.plot_window.setLabel('left', y_axis_label, **label_style)
        self.plot_item = self.plot_window.getPlotItem()
        self.view_box = self.plot_item.getViewBox()
        self.left_side_layout.addWidget(self.plot_window)

        # keep track of visible data items
        self.visible_plot_data_items = 0

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

        # create the pyqtgraph PlotDataItems
        self.dnncv = {}
        for i in range(1, constants.NUM_DETECTORS + 1):
            key_cv = 'D%2.2iCV' % i
            self.dnncv[key_cv] = pg.PlotDataItem(name=key_cv, **line_style_list[i - 1])

        # create, add, and connect movable vertical and horizontal lines
        self.vline_min = pg.InfiniteLine(pos=-0.3, angle=90, pen='b', movable=True)
        self.vline_mid = pg.InfiniteLine(pos=0.0, angle=90, pen={'color': 'r', 'style': qtc.Qt.DashLine}, movable=False)
        self.vline_max = pg.InfiniteLine(pos=0.3, angle=90, pen='b', movable=True)
        self.hline_min = pg.InfiniteLine(pos=-10.0, angle=0, pen='b', movable=True)
        self.hline_mid = pg.InfiniteLine(pos=0.0, angle=0, pen={'color': 'r', 'style': qtc.Qt.DashLine}, movable=False)
        self.hline_max = pg.InfiniteLine(pos=10.0, angle=0, pen='b', movable=True)

        self.plot_window.addItem(self.vline_min)
        self.plot_window.addItem(self.vline_mid)
        self.plot_window.addItem(self.vline_max)
        self.plot_window.addItem(self.hline_min)
        self.plot_window.addItem(self.hline_mid)
        self.plot_window.addItem(self.hline_max)

        # overrides will allow user to drag lines during realtime plot
        self.temporary_vline_override = False
        self.temporary_hline_override = False

        self.vline_min.sigPositionChanged.connect(self.vline_moved)
        self.vline_max.sigPositionChanged.connect(self.vline_moved)
        self.hline_min.sigPositionChanged.connect(self.hline_moved)
        self.hline_max.sigPositionChanged.connect(self.hline_moved)

        self.vline_min.sigDragged.connect(self.activate_vline_override)
        self.vline_max.sigDragged.connect(self.activate_vline_override)
        self.hline_min.sigDragged.connect(self.activate_hline_override)
        self.hline_max.sigDragged.connect(self.activate_hline_override)

        '''
        Right side
        '''

        '''File control'''

        # create file control groupbox and add to the right side layout
        self.file_control = qtw.QGroupBox()
        self.file_control.setTitle('File Control')
        self.file_control_layout = qtw.QGridLayout()
        self.file_control.setLayout(self.file_control_layout)
        self.right_side_layout.addWidget(self.file_control)

        # create file control widgets
        self.file_path_label = qtw.QLabel('File path')
        self.file_path_ledit = qtw.QLineEdit()
        self.load_file_button = qtw.QPushButton('Load data')
        self.file_name_label = qtw.QLabel('File name')
        self.file_name_ledit = qtw.QLineEdit()
        self.current_file_decrement_button = qtw.QPushButton('<')
        self.current_file_increment_button = qtw.QPushButton('>')

        # connect signal to slots
        self.load_file_button.clicked.connect(lambda: controller.load_new_data(self.load_file_button.text()))
        self.current_file_decrement_button.clicked.connect(lambda: controller.load_new_data(self.current_file_decrement_button.text()))
        self.current_file_increment_button.clicked.connect(lambda: controller.load_new_data(self.current_file_increment_button.text()))

        # add file control widgets to the file control groupbox
        self.file_control_layout.addWidget(self.file_path_label, 0, 0)
        self.file_control_layout.addWidget(self.file_path_ledit, 0, 1, 1, 3)
        self.file_control_layout.addWidget(self.load_file_button, 0, 4, 1, 2)
        self.file_control_layout.addWidget(self.file_name_label, 1, 0)
        self.file_control_layout.addWidget(self.file_name_ledit, 1, 1, 1, 3)
        self.file_control_layout.addWidget(self.current_file_decrement_button, 1, 4)
        self.file_control_layout.addWidget(self.current_file_increment_button, 1, 5)



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

        # connect signals to slots
        self.reset_vertical_markers_button.clicked.connect(self.reset_vertical_markers)
        self.reset_horizontal_markers_button.clicked.connect(self.reset_horizontal_markers)
        self.reset_all_markers_button.clicked.connect(self.reset_all_markers)

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

        # connect signals to slots
        self.active_horizontal_axis_combo.currentIndexChanged.connect(controller.update_active_positioner)
        self.hax_vline_min_position_button.clicked.connect(lambda: controller.move_active_positioner(self.hax_vline_min_position_button.text()))
        self.hax_vline_mid_position_button.clicked.connect(lambda: controller.move_active_positioner(self.hax_vline_mid_position_button.text()))
        self.hax_vline_max_position_button.clicked.connect(lambda: controller.move_active_positioner(self.hax_vline_max_position_button.text()))

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
        self.detectors_control_layout = qtw.QVBoxLayout()
        self.detectors_control.setLayout(self.detectors_control_layout)
        self.right_side_layout.addWidget(self.detectors_control)

        self.detectors_tab_widget = qtw.QTabWidget()
        self.detectors_control_layout.addWidget(self.detectors_tab_widget)

        # create dictionary of QCheckBox to toggle visibility of active detectors
        self.dnncb = {}
        num_tabs = constants.NUM_DETECTORS // 10
        for i in range(num_tabs):
            detectors_tab = qtw.QWidget()
            detectors_tab_layout = qtw.QVBoxLayout()
            detectors_tab.setLayout(detectors_tab_layout)
            for j in range(10):
                number = i * 10 + 1 + j
                key_cb = 'D%2.2iCB' % number
                h_layout = qtw.QHBoxLayout()
                d_label = qtw.QLabel(key_cb[:3])
                d_label.setFixedWidth(30)
                self.dnncb[key_cb] = qtw.QCheckBox()
                self.dnncb[key_cb].stateChanged.connect(self.det_cbox_toggled)
                h_layout.addWidget(d_label)
                h_layout.addWidget(self.dnncb[key_cb])
                detectors_tab_layout.addLayout(h_layout)
            label_min = i * 10 + 1
            label_max = label_min + 9
            self.detectors_tab_widget.addTab(detectors_tab, f'{label_min} - {label_max}')

        '''Windows control'''

        # create windows control groupbox and add to right side layout
        self.windows_control = qtw.QGroupBox()
        self.windows_control.setTitle('Windows Control')
        self.windows_control_layout = qtw.QHBoxLayout()
        self.windows_control.setLayout(self.windows_control_layout)
        self.right_side_layout.addWidget(self.windows_control)

        # create windows control widgets
        self.test_button = qtw.QPushButton('Test')
        self.overlays_button = qtw.QPushButton('Overlays')
        self.abort_button = qtw.QPushButton('Abort')
        self.quit_button = qtw.QPushButton('Quit')

        # connect signals to slots
        self.test_button.clicked.connect(self.test_button_clicked)

        # add windows control widgets to windows control groupbox
        self.windows_control_layout.addWidget(self.test_button)
        self.windows_control_layout.addWidget(self.overlays_button)
        self.windows_control_layout.addWidget(self.abort_button)
        self.windows_control_layout.addWidget(self.quit_button)

    def vline_moved(self):
        v_min = self.vline_min.getXPos()
        v_max = self.vline_max.getXPos()
        v_mid = (v_min + v_max) / 2.0
        v_width = v_max - v_min
        self.vline_mid.setValue(v_mid)
        self.hax_vline_min_position_button.setText('%.3f' % v_min)
        self.hax_vline_mid_position_button.setText('%.3f' % v_mid)
        self.hax_vline_max_position_button.setText('%.3f' % v_max)
        self.hax_vline_markers_width.setText('%.4f' % v_width)

    def hline_moved(self):
        h_min = self.hline_min.getYPos()
        h_max = self.hline_max.getYPos()
        h_mid = (h_min + h_max) / 2.0
        h_width = h_max - h_min
        self.hline_mid.setValue(h_mid)
        self.vax_hline_min_position_button.setText('%.3f' % h_min)
        self.vax_hline_mid_position_button.setText('%.3f' % h_mid)
        self.vax_hline_max_position_button.setText('%.3f' % h_max)
        self.vax_hline_markers_width.setText('%.4f' % h_width)

    def activate_vline_override(self):
        self.temporary_vline_override = True

    def activate_hline_override(self):
        self.temporary_hline_override = True

    def reset_vertical_markers(self):
        if not self.visible_plot_data_items == 1:
            return
        self.temporary_vline_override = False
        for key_cb in self.dnncb:
            if self.dnncb[key_cb].isChecked():
                key_cv = key_cb.replace('B', 'V')
                h_min = self.hline_min.getYPos()
                h_max = self.hline_max.getYPos()
                h_mid = (h_min + h_max) / 2.0
                x_crossing_points = []
                x_points = self.dnncv[key_cv].getData()[0]
                y_points = self.dnncv[key_cv].getData()[1]
                for i in range(x_points.size - 1):
                    if y_points[i] < h_mid <= y_points[i + 1] or y_points[i + 1] < h_mid <= y_points[i]:
                        y2, y1, x2, x1 = y_points[i + 1], y_points[i], x_points[i + 1], x_points[i]
                        m = (y2 - y1) / (x2 - x1)
                        x_crossing_point = (h_mid - y1) / m + x1
                        x_crossing_points.append(x_crossing_point)
                if len(x_crossing_points) > 1:
                    self.vline_min.setValue(x_crossing_points[0])
                    self.vline_max.setValue(x_crossing_points[-1])
                break

    def reset_horizontal_markers(self):
        if self.visible_plot_data_items == 0:
            return
        self.temporary_hline_override = False
        y_minimums = []
        y_maximums = []
        for key_cb in self.dnncb:
            if self.dnncb[key_cb].isChecked():
                key_cv = key_cb.replace('B', 'V')
                y_min, y_max = self.dnncv[key_cv].dataBounds(1)
                y_minimums.append(y_min)
                y_maximums.append(y_max)
        try:
            data_y_min = min(y_minimums)
            data_y_max = max(y_maximums)
            self.hline_min.setValue(data_y_min)
            self.hline_max.setValue(data_y_max)
        except TypeError:
            return

    def reset_all_markers(self):
        self.reset_horizontal_markers()
        self.reset_vertical_markers()

    def det_cbox_toggled(self):
        item_list = self.plot_window.listDataItems()
        for key_cb in self.dnncb:
            key_cv = key_cb.replace('B', 'V')
            if self.dnncb[key_cb].isChecked() and self.dnncv[key_cv] not in item_list:
                self.plot_window.addItem(self.dnncv[key_cv])
                self.visible_plot_data_items += 1
            elif not self.dnncb[key_cb].isChecked() and self.dnncv[key_cv] in item_list:
                self.plot_window.removeItem(self.dnncv[key_cv])
                self.visible_plot_data_items -= 1
        self.view_box.enableAutoRange(axis='y')

    def clear_plots(self):
        for each in self.dnncv:
            self.dnncv[each].clear()
            self.dnncv[each].updateItems()

    def initialize_plot_window_y_range(self):
        y_min, y_max = -10, 10
        y_axis_label = 'Counts'
        label_style = {'color': '#808080', 'font': ' bold 16px'}
        self.plot_window.setYRange(y_min, y_max)
        self.plot_window.setLabel('left', y_axis_label, **label_style)
        self.hline_min.setValue(y_min)
        self.hline_max.setValue(y_max)

    def test_button_clicked(self):
        short_path = caget('16test:saveData_fullPathName', as_string=True)
        print(short_path)
        fs = caget('16test:saveData_fileSystem')
        sd = caget('16test:saveData_subDir')
        long_path = f'{fs}/{sd}'
        print(long_path)
        sfname = qtw.QFileDialog.getOpenFileName(directory=short_path)
        lfname = qtw.QFileDialog.getOpenFileName(directory=long_path)
        print(sfname, lfname)


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    controller = None
    gui = PyQtView(controller)
    gui.show()
    sys.exit(app.exec_())

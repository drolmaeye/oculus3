import sys
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg
import pyqtgraph as pg
import numpy as np
from epics import PV, caget, caput
from epics.devices import Scan
import time
import os
import constants
from oculus3_v0_core import CoreData
from oculus3_v0_view import PyQtView


class MainWindow(qtw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1080, 720)
        self.setWindowTitle('Oculus')
        self.setWindowIcon(qtg.QIcon('eye1.png'))


class OculusController(qtc.QObject):

    realtime_scandata_modified_signal = qtc.pyqtSignal()
    scan_start_stop_signal = qtc.pyqtSignal(int)

    def __init__(self, root, stump):
        super().__init__()

        # create references to the model and view
        self.model = CoreData(root, stump)
        self.view = PyQtView(self)

        # create real-time scan activity PVs
        self.val = PV(self.model.trunk + 'VAL')
        self.data = PV(self.model.trunk + 'DATA')
        self.cpt = PV(self.model.trunk + 'CPT')
        self.npts = PV(self.model.trunk + 'NPTS')
        # add callbacks (after connection is established)
        self.val.wait_for_connection()
        self.val.add_callback(self.val_triggered)
        self.data.wait_for_connection()
        self.data.add_callback(self.data_triggered)

        # create a variable to hold total number of scan points
        self.num_points = 11

        # connect signals to slots
        self.realtime_scandata_modified_signal.connect(self.update_realtime_scandata)
        self.scan_start_stop_signal.connect(self.initialize_finalize_scan)

    def startup_sequence(self):
        self.view.show()
        self.update_gui_positioner_names()
        self.update_gui_detector_names()

    def update_active_positioner(self, index):
        if index < 0:
            return
        n = index + 1
        self.update_plot_window_domain(n)

    def move_active_positioner(self, text):
        # move positioner only if scan is not active
        if self.data.value:
            n = self.view.active_horizontal_axis_combo.currentIndex() + 1
            caput(self.model.pnpv[f'P{n}PV'].value, text)

    # EPICS callbacks
    def val_triggered(self, **kwargs):
        return self.realtime_scandata_modified_signal.emit()

    def data_triggered(self, value, **kwargs):
        return self.scan_start_stop_signal.emit(value)

    # PyQtSlots
    def update_realtime_scandata(self):
        current_index = self.cpt.value - 1
        for positioners in self.model.active_positioners_arrays:
            self.model.active_positioners_arrays[positioners][current_index] = self.model.rncv[positioners].value
        n = self.view.active_horizontal_axis_combo.currentIndex() + 1
        self.model.current_x_values[:current_index + 1] = self.model.active_positioners_arrays[f'R{n}CV'][:current_index + 1]
        for detectors in self.model.active_detectors_arrays:
            self.model.active_detectors_arrays[detectors][current_index] = self.model.dnncv[detectors].value
            if current_index > 0:
                self.view.dnncv[detectors].setData(self.model.current_x_values[:current_index + 1],
                                                   self.model.active_detectors_arrays[detectors][:current_index + 1])
        self.view.view_box.enableAutoRange(axis='y')
        if not self.view.temporary_hline_override:
            self.view.reset_horizontal_markers()


    def initialize_finalize_scan(self, value):
        if value == 0:
            print('scan is starting')
            # scan is starting
            self.view.temporary_vline_override = False
            self.view.temporary_hline_override = False
            if self.model.positioners_modified_flag:
                self.update_gui_positioner_names()
            if self.model.detectors_modified_flag:
                self.update_gui_detector_names()
            n = self.view.active_horizontal_axis_combo.currentIndex() + 1
            self.update_plot_window_domain(n)
            y_min, y_max = -10, 10
            y_axis_label = 'Counts'
            label_style = {'color': '#808080', 'font': ' bold 16px'}
            self.view.plot_window.setYRange(y_min, y_max)
            self.view.plot_window.setLabel('left', y_axis_label, **label_style)
            self.view.hline_min.setValue(y_min)
            self.view.hline_max.setValue(y_max)
        else:
            print('scan is finsihed')
            # in reality, probably need to plot DddDA and PnRA arrays
            self.num_points = self.cpt.value
            for positioners in self.model.active_positioners_arrays:
                print(self.model.active_positioners_arrays[positioners][:self.num_points])
            for detectors in self.model.active_detectors_arrays:
                print(self.model.active_detectors_arrays[detectors][:self.num_points])
            if not self.view.temporary_hline_override:
                self.view.reset_horizontal_markers()
            if not self.view.temporary_vline_override:
                self.view.reset_vertical_markers()

    def update_gui_positioner_names(self):
        self.model.positioners_modified_flag = False
        self.view.active_horizontal_axis_combo.clear()
        for positioners in self.model.active_positioners_names:
            text = self.model.active_positioners_names[positioners]
            self.view.active_horizontal_axis_combo.addItem(text)

    def update_gui_detector_names(self):
        self.model.detectors_modified_flag = False
        for detectors in self.model.active_detectors_names:
            key_cb = detectors.replace('PV', 'CB')
            self.view.dnncb[key_cb].setText(self.model.active_detectors_names[detectors])

    def update_plot_window_domain(self, n):
        if self.data.value:
            x_min = self.model.pnpv[f'P{n}RA'].value[0]
            x_max = self.model.pnpv[f'P{n}RA'].value[self.cpt.value - 1]
        else:
            pp = self.model.pnpv[f'P{n}PP'].value
            sp = self.model.pnpv[f'P{n}SP'].value
            ep = self.model.pnpv[f'P{n}EP'].value
            if self.model.pnpv[f'P{n}AR'].value == 1:
                x_min = pp + sp
                x_max = pp + ep
            else:
                x_min = sp
                x_max = ep
        width = x_max - x_min
        x_axis_label = self.view.active_horizontal_axis_combo.currentText()
        label_style = {'color': '#808080', 'font': ' bold 16px'}
        self.view.plot_window.setXRange(x_min, x_max)
        self.view.plot_window.setLabel('bottom', x_axis_label, **label_style)
        self.view.vline_min.setValue(x_min + width * 0.25)
        self.view.vline_max.setValue(x_min + width * 0.75)

    def update_plot_window_range(self, initialize):
        if initialize:
            y_min, y_max = -10, 10
        else:
            y_minimums = []
            y_maximums = []
            item_list = self.view.plot_window.listDataItems()
            for items in item_list:
                y_bounds = items.dataBounds(1)
                y_minimums.append(y_bounds[0])
                y_maximums.append(y_bounds[1])
            print(y_minimums, y_maximums)
            y_min, y_max = min(y_minimums), max(y_maximums)
        y_axis_label = 'Counts'
        label_style = {'color': '#808080', 'font': ' bold 16px'}
        self.view.plot_window.setYRange(y_min, y_max)
        self.view.plot_window.setLabel('left', y_axis_label, **label_style)
        self.view.hline_min.setValue(y_min)
        self.view.hline_max.setValue(y_max)


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    crate, scann = '16test:', 'scan1.'
    controller = OculusController(crate, scann)
    controller.startup_sequence()
    sys.exit(app.exec_())

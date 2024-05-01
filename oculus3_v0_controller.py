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
import mda


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

        # file management PVs

        # create a variable to hold total number of scan points
        self.num_points = 11

        # connect signals to slots
        self.realtime_scandata_modified_signal.connect(self.update_realtime_scandata)
        self.scan_start_stop_signal.connect(self.initialize_finalize_scan)

    def startup_sequence(self):
        self.update_gui_positioner_names()
        self.update_gui_detector_names()
        self.view.show()
        # print(self.view.file_control.size())

    def load_new_data(self, text):
        # get the current file path for opening or building new filename
        fsystem = self.model.file_path_fs.value
        fsubdir = self.model.file_path_sd.value
        if fsubdir:
            fpath = f'{fsystem}/{fsubdir}'
        else:
            fpath = fsystem
        if text == 'Load data':
            # use browses filesystem for new filename
            fname, fext = qtw.QFileDialog.getOpenFileName(directory=fpath, filter='mda files (*.mda)')
        else:
            # current file is incremented or decremented by one
            current_tail = self.view.file_name_ledit.text()
            current_fnumber = current_tail[(current_tail.rfind('_') + 1):-4]
            fill_length = len(current_fnumber)
            if text == '<':
                new_fnumber = int(current_fnumber) - 1
            else:
                new_fnumber = int(current_fnumber) + 1
            new_tail = current_tail.replace(current_fnumber, str(new_fnumber).zfill(fill_length))
            fname = f'{fpath}/{new_tail}'
        if os.path.isfile(fname):
            head, tail = os.path.split(fname)
            self.view.file_path_ledit.setText(head)
            self.view.file_name_ledit.setText(tail)
            dim = mda.readMDA(fname=fname, showHelp=0)
        else:
            print('no file to open')

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
        current_index = self.cpt.get(use_monitor=False) - 1
        for positioners in self.model.active_positioners_arrays:
            self.model.active_positioners_arrays[positioners][current_index] = self.model.rncv[positioners].value
        n = self.view.active_horizontal_axis_combo.currentIndex() + 1
        x_values = self.model.active_positioners_arrays[f'R{n}CV'][:current_index + 1]
        for detectors in self.model.active_detectors_arrays:
            self.model.active_detectors_arrays[detectors][current_index] = self.model.dnncv[detectors].value
            y_values = self.model.active_detectors_arrays[detectors][:current_index + 1]
            print(y_values)
            if current_index > 0:
                # derivative test start
                # y_values = self.model.active_detectors_arrays[detectors][:current_index + 1]
                if self.view.test_cbox.isChecked():
                    x_length = len(x_values)
                    y_temp = np.zeros(len(y_values))
                    for x in range(x_length):
                        if x == 0 or x == x_length - 1:
                            pass
                        else:
                            dy = y_values[x + 1] - y_values[x - 1]
                            dx = x_values[x + 1] - x_values[x - 1]
                            y_temp[x] = dy/dx
                    y_temp[0] = y_temp[1]
                    y_temp[-1] = y_temp[-2]
                    y_values = y_temp
                self.view.dnncv[detectors].setData(x_values, y_values)
                # derivative test end
                # self.view.dnncv[detectors].setData(x_values, self.model.active_detectors_arrays[detectors][:current_index + 1])
        self.view.view_box.enableAutoRange(axis='y')
        if not self.view.temporary_hline_override:
            self.view.reset_horizontal_markers()

    def initialize_finalize_scan(self, value):
        if value == 0:
            print('scan is starting')
            # scan is starting
            self.view.clear_plots()
            self.view.temporary_vline_override = False
            self.view.temporary_hline_override = False
            if self.model.positioners_modified_flag:
                self.update_gui_positioner_names()
            if self.model.detectors_modified_flag:
                self.update_gui_detector_names()
            n = self.view.active_horizontal_axis_combo.currentIndex() + 1
            self.update_plot_window_domain(n)
        else:
            print('scan is finished')
            # in consider plotting DddDA and PnRA arrays
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


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    crate, scann = '16test:', 'scan1.'
    controller = OculusController(crate, scann)
    controller.startup_sequence()
    sys.exit(app.exec_())

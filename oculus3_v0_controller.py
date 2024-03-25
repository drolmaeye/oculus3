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
from oculus3_v0_core import CoreData


class MainWindow(qtw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1080, 720)
        self.setWindowTitle('Oculus')
        self.setWindowIcon(qtg.QIcon('eye1.png'))


class OculusController(qtc.QObject):

    realtime_scandata_modified_signal = qtc.pyqtSignal()
    scan_start_stop_signal = qtc.pyqtSignal()

    def __init__(self, model):
        super().__init__()
        # create references to the model and view
        self.model = model
        # self.view = view

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

        # connect signals to slots
        self.realtime_scandata_modified_signal.connect(self.update_realtime_scandata)
        self.scan_start_stop_signal.connect(self.initialize_finalize_scan)

    # EPICS callbacks
    def val_triggered(self, **kwargs):
        return self.realtime_scandata_modified_signal.emit()

    def data_triggered(self, **kwargs):
        return self.scan_start_stop_signal.emit()

    # PyQtSlots
    def update_realtime_scandata(self):
        current_index = self.cpt.value - 1
        for positioners in self.model.active_positioners_position_arrays:
            self.model.active_positioners_position_arrays[positioners][current_index] = self.model.rncv[positioners].value
            print(self.model.active_positioners_position_arrays[positioners][:current_index + 1])
        for detectors in self.model.active_detectors_data_arrays:
            self.model.active_detectors_data_arrays[detectors][current_index] = self.model.dnncv[detectors].value
            print(self.model.active_detectors_data_arrays[detectors][:current_index + 1])

    def initialize_finalize_scan(self):
        pass
        # if self.data.value == 0:
        #     print('scan is starting')
        #     # scan is starting
        #     # self.update_pos_name_signal.emit()
        #     pp = self.pnpv['P1PP'].value
        #     sp = self.pnpv['P1SP'].value
        #     ep = self.pnpv['P1EP'].value
        #     if self.pnpv['P1AR'].value == 1:
        #         x_min = pp + sp
        #         x_max = pp + ep
        #     else:
        #         x_min = sp
        #         x_max = ep
        #     # TODO send these values out to GUI for initial draw
        #     # eye.pw.setXRange(x_min, x_max)
        #     # width = x_max - x_min
        #     # eye.vline_min.setX(x_min + width * 0.25)
        #     # eye.vline_mid.setX(x_min + width * 0.50)
        #     # eye.vline_max.setX(x_min + width * 0.75)
        # else:
        #     # scan is ending
        #     print('scan is finsihed')
        #     # in reality, probably need to plot DddDA and PnRA arrays
        #     num_points = self.npts.value
        #     print(self.x_values[:num_points])
        #     for detectors in self.active_detectors:
        #         print(self.active_detectors[detectors][:num_points])

if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    crate, scann = '16test:', 'scan1.'
    # core = CoreData(root=crate, stump=scann)
    # core.active_detectors_modified_signal.emit()
    controller = OculusController(CoreData(crate, scann))
    # stuff below should just go in a startup method within controller
    controller.model.active_positioners_modified_signal.emit()
    controller.model.active_detectors_modified_signal.emit()
    gui = MainWindow()
    gui.show()
    sys.exit(app.exec_())

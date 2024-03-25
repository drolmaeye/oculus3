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


class CoreData(qtc.QObject):
    NUM_POSITIONERS = 4
    NUM_TRIGGERS = 2
    NUM_DETECTORS = 70
    MAX_NUM_POINTS = 1000

    # attributes to build the positioner dictionary Pnpv, including:
    # pv, name, p0, min, center, max, step, width, scan mode, abs/rel, and readback array
    pos_attrs = ('PV', 'NV', 'PP', 'SP', 'CP', 'EP', 'SI', 'WD', 'SM', 'AR', 'RA')

    active_positioners_modified_signal = qtc.pyqtSignal()
    active_detectors_modified_signal = qtc.pyqtSignal()
    realtime_scandata_modified_signal = qtc.pyqtSignal()
    scan_start_stop_signal = qtc.pyqtSignal()

    def __init__(self, root, stump):
        super().__init__()

        '''
        create empty core data dictionaries, including:
        Pnpv PVs (see class pos_attrs), readback current value
        Detector PVs, name valids, current values, and final data arrays
        '''

        self.pnpv = {}
        self.rncv = {}

        self.dnnpv = {}
        self.dnnnv = {}
        self.dnncv = {}
        self.dnnda = {}

        '''
        Create dictionaries to hold the real-time scan results (np.arrays)
        and names for active positioners and detectors
        '''

        self.active_positioners_position_arrays = {}
        self.active_positioners_names = {}
        self.active_detectors_data_arrays = {}
        self.active_detectors_names = {}

        # combine ioc prefix with scan number to generate PV trunk
        self.trunk = root + stump

        # flags to indicate if positioners or detectors have been modified
        self.positioners_modified_flag = True
        self.detectors_modified_flag = True

        # initialize PVs in dictionaries
        for i in range(1, CoreData.NUM_POSITIONERS + 1):
            for a in CoreData.pos_attrs:
                key_pnpv = 'P%i%s' % (i, a)
                self.pnpv[key_pnpv] = PV(self.trunk + key_pnpv)
                if a == 'PV':
                    self.pnpv[key_pnpv].wait_for_connection()
                    self.pnpv[key_pnpv].add_callback(self.positioners_modified)
            key_rncv = 'R%iCV' % i
            self.rncv[key_rncv] = PV(self.trunk + key_rncv)

        for i in range(1, CoreData.NUM_DETECTORS + 1):
            key_pv = 'D%2.2iPV' % i
            key_nv = 'D%2.2iNV' % i
            key_cv = 'D%2.2iCV' % i
            key_da = 'D%2.2iDA' % i
            self.dnnpv[key_pv] = PV(self.trunk + key_pv)
            self.dnnnv[key_nv] = PV(self.trunk + key_nv)
            self.dnncv[key_cv] = PV(self.trunk + key_cv)
            self.dnnda[key_da] = PV(self.trunk + key_da)
            # add callback to DnnPV (after connection is established)
            self.dnnpv[key_pv].wait_for_connection()
            self.dnnpv[key_pv].add_callback(self.detectors_modified)

        # create positioner- and detector-independent PVs
        self.val = PV(self.trunk + 'VAL')
        self.data = PV(self.trunk + 'DATA')
        self.cpt = PV(self.trunk + 'CPT')
        self.npts = PV(self.trunk + 'NPTS')
        # add callbacks for independent PVs (after connections are established)
        self.val.wait_for_connection()
        self.val.add_callback(self.val_triggered)
        self.data.wait_for_connection()
        self.data.add_callback(self.data_triggered)

        # connect signals to slots
        self.active_positioners_modified_signal.connect(self.update_active_positioners)
        self.active_detectors_modified_signal.connect(self.update_active_detectors)
        self.realtime_scandata_modified_signal.connect(self.update_realtime_scandata)
        self.scan_start_stop_signal.connect(self.initialize_finalize_scan)

    # EPICS callbacks
    def positioners_modified(self, pvname, **kwargs):
        self.positioners_modified_flag = True
        return self.active_positioners_modified_signal.emit()

    def detectors_modified(self, **kwargs):
        self.detectors_modified_flag = True
        return self.active_detectors_modified_signal.emit()

    def val_triggered(self, **kwargs):
        return self.realtime_scandata_modified_signal.emit()

    def data_triggered(self, **kwargs):
        return self.scan_start_stop_signal.emit()

    # pyqtSlots
    def update_active_positioners(self):
        # clear existing dictionaries
        self.active_positioners_position_arrays.clear()
        self.active_positioners_names.clear()
        for i in range(1, CoreData.NUM_POSITIONERS + 1):
            nv_branch = 'P%iNV' % i
            pv_key = 'P%iPV' % i
            pos_key = 'R%iCV' % i
            if caget(self.trunk + nv_branch) == 0:
                # fill active positioners data arrays dict with dummy arrays
                self.active_positioners_position_arrays[pos_key] = np.zeros(CoreData.MAX_NUM_POINTS)
                # fill active positioners names arrays with common or PV names
                new_trunk = self.pnpv[pv_key].value.rsplit('.')[0]
                record_type = caget(new_trunk + '.RTYP')
                if record_type == 'motor':
                    name = caget(new_trunk + '.DESC')
                else:
                    name = self.pnpv[pv_key].value
                self.active_positioners_names[pv_key] = name

    def update_active_detectors(self):
        self.active_detectors_data_arrays.clear()
        self.active_detectors_names.clear()
        for i in range(1, CoreData.NUM_DETECTORS + 1):
            nv_branch = 'D%2.2iNV' % i
            pv_key = 'D%2.2iPV' % i
            det_key = 'D%2.2iCV' % i
            #  check to see if detector PV has been accepted by EPICS
            if caget(self.trunk + nv_branch) == 0:
                # fill active detectors data arrays dict with dummy arrays
                self.active_detectors_data_arrays[det_key] = np.zeros(CoreData.MAX_NUM_POINTS)
                # fill active detectors names arrays with common or PV names
                new_trunk = self.dnnpv[pv_key].value.rsplit('.')[0]
                new_branch = '.' + self.dnnpv[pv_key].value.rsplit('.')[1]
                record_type = caget(new_trunk + '.RTYP')
                if record_type == 'scaler':
                    if '.S' in new_branch:
                        name_branch = new_branch.replace('S', 'NM')
                        name = caget(new_trunk + name_branch)
                    elif '.T' in new_branch:
                        name = 'Elapsed Time'
                    else:
                        name = ''
                elif record_type == 'transform':
                    name_branch = new_branch[:1] + 'CMT' + new_branch[1:]
                    name = caget(new_trunk + name_branch)
                elif record_type == 'mca':
                    name_branch = new_branch + 'NM'
                    name = caget(new_trunk + name_branch)
                else:
                    name = ''
                if name:
                    self.active_detectors_names[pv_key] = name
                else:
                    self.active_detectors_names[pv_key] = self.dnnpv[pv_key].value

    def update_realtime_scandata(self):
        current_index = self.cpt.value - 1
        for positioners in self.active_positioners_position_arrays:
            self.active_positioners_position_arrays[positioners][current_index] = self.rncv[positioners].value
            print(self.active_positioners_position_arrays[positioners][:current_index + 1])
        for detectors in self.active_detectors_data_arrays:
            self.active_detectors_data_arrays[detectors][current_index] = self.dnncv[detectors].value
            print(self.active_detectors_data_arrays[detectors][:current_index + 1])

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
    core = CoreData(root=crate, stump=scann)
    core.active_detectors_modified_signal.emit()
    gui = MainWindow()
    gui.show()
    sys.exit(app.exec_())

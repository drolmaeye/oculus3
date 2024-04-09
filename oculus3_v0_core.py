import sys
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
import numpy as np
from epics import PV, caget
import constants


class MainWindow(qtw.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 540, 360)
        self.setWindowTitle('Oculus')


class CoreData(qtc.QObject):
    # class attributes to build the positioner dictionary pnpv, including:
    # pv, name, p0, min, center, max, step, width, scan mode, abs/rel, and readback array
    pos_attrs = ('PV', 'NV', 'PP', 'SP', 'CP', 'EP', 'SI', 'WD', 'SM', 'AR', 'RA')

    # PyQt Signals
    active_positioners_modified_signal = qtc.pyqtSignal(str)
    active_detectors_modified_signal = qtc.pyqtSignal(str)

    def __init__(self, root, stump):
        super().__init__()

        '''
        create empty core data dictionaries, including:
        
        Several positioner PVs (see class pos_attrs)
        Readback current value
        
        Detector PVs
        Name valids
        Current values
        Final data arrays
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

        self.active_positioners_arrays = {}
        self.active_positioners_names = {}
        self.active_detectors_arrays = {}
        self.active_detectors_names = {}

        self.current_x_values = np.zeros(constants.MAX_NUM_POINTS)

        # combine ioc prefix with scan number to generate PV trunk
        # note that stump should end in a dot (e.g., 'scan1.')
        self.trunk = root + stump

        # flags to indicate if positioners or detectors have been modified
        self.positioners_modified_flag = True
        self.detectors_modified_flag = True

        # create Positioner PVs and add to existing dictionaries
        for i in range(1, constants.NUM_POSITIONERS + 1):
            for a in CoreData.pos_attrs:
                key_pnpv = 'P%i%s' % (i, a)
                self.pnpv[key_pnpv] = PV(self.trunk + key_pnpv)
                if a == 'PV':
                    self.pnpv[key_pnpv].wait_for_connection()
                    self.pnpv[key_pnpv].add_callback(self.positioners_modified)
            key_rncv = 'R%iCV' % i
            self.rncv[key_rncv] = PV(self.trunk + key_rncv)

        # create detector PVs and add to existing dictionaries
        for i in range(1, constants.NUM_DETECTORS + 1):
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

        # connect signals to slots
        self.active_positioners_modified_signal.connect(self.update_active_positioner)
        self.active_detectors_modified_signal.connect(self.update_active_detector)

        # fill active positioner and detector arrays on program start
        self.initialize_active_positioners()
        self.initialize_active_detectors()

    # EPICS callbacks
    def positioners_modified(self, pvname, **kwargs):
        self.positioners_modified_flag = True
        return self.active_positioners_modified_signal.emit(pvname)

    def detectors_modified(self, pvname, **kwargs):
        self.detectors_modified_flag = True
        return self.active_detectors_modified_signal.emit(pvname)

    def update_active_positioner(self, pvname):
        n = pvname[-3]
        validity = caget(self.trunk + f'P{n}NV', use_monitor=False)
        if validity == 0:
            self.active_positioners_arrays[f'R{n}CV'] = np.zeros(constants.MAX_NUM_POINTS)
            self.update_active_positioners_names(n)
        else:
            if f'R{n}CV' in self.active_positioners_arrays:
                del self.active_positioners_arrays[f'R{n}CV']
                del self.active_positioners_names[f'P{n}PV']

    def update_active_detector(self, pvname):
        nn = pvname[-4:-2]
        validity = caget(self.trunk + f'D{nn}NV', use_monitor=False)
        if validity == 0:
            self.active_detectors_arrays[f'D{nn}CV'] = np.zeros(constants.MAX_NUM_POINTS)
            self.update_active_detectors_names(nn)
        else:
            if f'D{nn}CV' in self.active_detectors_arrays:
                del self.active_detectors_arrays[f'D{nn}CV']
                del self.active_detectors_names[f'D{nn}PV']

    def update_active_positioners_names(self, n):
        # either get a proper motor name or just identify by PV name
        if '.' in self.pnpv[f'P{n}PV'].value:
            new_trunk = self.pnpv[f'P{n}PV'].value.rsplit('.')[0]
            record_type = caget(new_trunk + '.RTYP')
            if record_type == 'motor':
                description = caget(new_trunk + '.DESC')
                if description:
                    name = description
                else:
                    name = self.pnpv[f'P{n}PV'].value
            else:
                name = self.pnpv[f'P{n}PV'].value
        else:
            name = self.pnpv[f'P{n}PV'].value
        self.active_positioners_names[f'P{n}PV'] = name

    def update_active_detectors_names(self, nn):
        if '.' in self.dnnpv[f'D{nn}PV'].value:
            new_trunk = self.dnnpv[f'D{nn}PV'].value.rsplit('.')[0]
            new_branch = '.' + self.dnnpv[f'D{nn}PV'].value.rsplit('.')[1]
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
                self.active_detectors_names[f'D{nn}PV'] = name
            else:
                self.active_detectors_names[f'D{nn}PV'] = self.dnnpv[f'D{nn}PV'].value

    def initialize_active_positioners(self):
        for n in range(1, constants.NUM_POSITIONERS + 1):
            if self.pnpv[f'P{n}NV'].value == 0:
                self.active_positioners_arrays[f'R{n}CV'] = np.zeros(constants.MAX_NUM_POINTS)
                self.update_active_positioners_names(n)

    def initialize_active_detectors(self):
        for i in range(1, constants.NUM_DETECTORS + 1):
            nn = '%2.2i' % i
            if self.dnnnv[f'D{nn}NV'].value == 0:
                self.active_detectors_arrays[f'D{nn}CV'] = np.zeros(constants.MAX_NUM_POINTS)
                self.update_active_detectors_names(nn)


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    crate, scann = '16test:', 'scan1.'
    core = CoreData(root=crate, stump=scann)
    gui = MainWindow()
    gui.show()
    sys.exit(app.exec_())

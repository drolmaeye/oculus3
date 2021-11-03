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

print('Oculus!')

class MainWindow(qtw.QMainWindow):

    def __init__(self):
        super().__init__()
        self.setGeometry(100, 100, 1080, 720)
        self.setWindowTitle('Oculus Machina development version')
        self.setWindowIcon(qtg.QIcon('eye1.png'))

        self.show()


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    w = MainWindow()
    sys.exit(app.exec_())

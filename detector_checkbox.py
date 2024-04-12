import sys
from PyQt5 import QtWidgets as qtw
from PyQt5 import QtCore as qtc
from PyQt5 import QtGui as qtg
import pyqtgraph as pg
from pyqtgraph.graphicsItems.LegendItem import ItemSample


class Window(qtw.QWidget):

    def __init__(self, item, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # self.setFixedHeight(80)
        main_layout = qtw.QHBoxLayout()
        self.setLayout(main_layout)

        self.detector_label = qtw.QLabel()
        self.detector_cbox = qtw.QCheckBox()
        self.detector_rep = pg.GraphicsLayoutWidget(parent=self)

        self.detector_label.setText('D01')
        self.detector_label.setFixedWidth(10)
        self.detector_cbox.setText('PVnn')

        main_layout.addWidget(self.detector_label)
        main_layout.addWidget(self.detector_cbox)
        main_layout.addWidget(self.detector_rep)

        # self.pdi = pg.PlotDataItem()
        self.sample = ItemSample(item)
        # print(self.sample.boundingRect())
        # print(type(self.sample))
        # print(self.sample.pixelHeight())
        # print(self.sample.pixelWidth())

        self.detector_rep.addItem(self.sample)

    def setText(self, text):
        self.detector_cbox.setText(text)




        # code ends here


if __name__ == '__main__':
    app = qtw.QApplication(sys.argv)
    w = Window()
    w.show()
    sys.exit(app.exec_())

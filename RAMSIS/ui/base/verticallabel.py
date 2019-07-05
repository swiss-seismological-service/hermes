"""
A QLabel that draws vertically
    
Copyright (C) 2018, SED (ETH Zurich)

"""
from PyQt5.QtCore import QSize
from PyQt5.QtWidgets import QLabel
from PyQt5.QtGui import QPainter


class VerticalLabel(QLabel):

    def paintEvent(self, e):
        w = self.width()
        h = self.height()
        painter = QPainter(self)
        painter.translate(w, 0)
        painter.rotate(90)
        painter.drawText(0, 0, h, w, self.alignment(), self.text())

    def sizeHint(self):
        return QSize(super().sizeHint().height(), super().sizeHint().width())

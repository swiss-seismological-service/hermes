"""
View level classes for parameter tree views
    
Copyright (C) 2018, SED (ETH Zurich)

"""

from PyQt5.QtCore import pyqtSignal
from PyQt5.QtWidgets import QStyledItemDelegate, QPushButton
from .model import ExtendNode


# Parameter Tree View

class ExtensibleNodeDelegate(QStyledItemDelegate):

    extend = pyqtSignal(object)

    def __init__(self, parent):
        super().__init__(parent)

    def paint(self, painter, option, index):
        node = index.internalPointer()
        item_view = self.parent()
        if isinstance(node, ExtendNode) \
                and not item_view.indexWidget(index)\
                and index.column() == 0:
            btn = QPushButton('+', item_view, clicked=self.on_button_clicked)
            btn.setProperty('node', node)
            btn.setFixedSize(40, 18)
            btn.setStyleSheet('margin-left: 5px; margin-top: 2px; border: 0px;'
                              'background-color: gray; color: white; '
                              'padding-top: -2; border-radius: 2px;')
            item_view.setIndexWidget(index, btn)
        else:
            super().paint(painter, option, index)

    def on_button_clicked(self, _):
        self.extend.emit(self.sender())

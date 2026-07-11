"""Edit OpOn"""

from PyQt5 import QtWidgets, uic

from .resources import resource_path


class OpOn(QtWidgets.QDialog):
    """Change the current operator"""

    def __init__(self, parent=None):
        super().__init__(parent)
        with resource_path("data/opon.ui") as data_path:
            uic.loadUi(data_path, self)
        self.buttonBox.clicked.connect(self.store)

    def store(self):
        """dialog magic"""

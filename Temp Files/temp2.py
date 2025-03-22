from PySide6.QtWidgets import QApplication, QWidget, QMessageBox
from PySide6.QtGui import QCloseEvent

class MyWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("My Widget")

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "Close Confirmation",
            "Are you sure you want to close?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    app = QApplication([])
    widget = MyWidget()
    widget.show()
    app.exec()
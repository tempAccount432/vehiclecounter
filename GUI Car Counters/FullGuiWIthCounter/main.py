import sys
from PySide6.QtWidgets import QApplication
from single_instance import SingleInstance
from gui import MainWindow

if __name__ == "__main__":
    instance_checker = SingleInstance()
    instance_checker.acquire()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
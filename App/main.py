import sys
from PySide6.QtWidgets import QApplication
# Import the MainWindow from our UI file
from ui import MainWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
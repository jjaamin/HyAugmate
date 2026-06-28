import sys
from PyQt6.QtWidgets import QApplication
from .window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    font = app.font()
    font.setPointSize(9)
    app.setFont(font)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())

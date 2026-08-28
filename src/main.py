# src/main.py
# 새로 버전 넣음
import sys
import os

# src 폴더 경로 보장
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication
from ui.main_window import OSCMasterTool


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = OSCMasterTool()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
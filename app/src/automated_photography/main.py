"""自動拍照GUI應用入口"""
import sys
from PySide6.QtWidgets import QApplication
from automated_photography.ui.main_window import AutoCameraGUI
from automated_photography.ui.styles import APP_STYLESHEET


def main():
    """應用主函數"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(APP_STYLESHEET)
    window = AutoCameraGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

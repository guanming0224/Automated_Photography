"""自動拍照GUI應用入口"""
import sys
from PySide6.QtWidgets import QApplication
from ui.main_window import AutoCameraGUI


def main():
    """應用主函數"""
    app = QApplication(sys.argv)
    window = AutoCameraGUI()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
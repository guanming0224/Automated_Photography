"""Application-wide Qt styles for the industrial console theme."""

APP_STYLESHEET = """
* {
    font-family: "Microsoft JhengHei UI", "Segoe UI", Arial;
    font-size: 13px;
    color: #172026;
}

QMainWindow,
QWidget#AppRoot,
QWidget#ControlPanel,
QWidget#PreviewPanel {
    background: #f1eee7;
}

QFrame#HeaderBar {
    background: #ffffff;
    border: 1px solid #d7dee2;
    border-radius: 8px;
}

QLabel#AppTitle {
    color: #172026;
    font-size: 20px;
    font-weight: 800;
}

QLabel#AppSubtitle,
QLabel#MutedLabel {
    color: #687981;
}

QLabel#HeaderBadge {
    background: #e6ecef;
    border: 1px solid #c9d4d9;
    border-radius: 6px;
    color: #41515c;
    font-weight: 700;
    padding: 6px 10px;
}

QLabel#HeaderBadge[status="success"] {
    background: #dff4e9;
    border-color: #8fd7b3;
    color: #0d6b3f;
}

QLabel#HeaderBadge[status="warning"] {
    background: #ffe2df;
    border-color: #f4aaa4;
    color: #b42318;
}

QScrollArea {
    background: transparent;
    border: 0;
}

QScrollArea > QWidget > QWidget {
    background: transparent;
}

QSplitter::handle {
    background: #c9d4d9;
    border-radius: 2px;
    margin: 8px 2px;
}

QGroupBox {
    background: #ffffff;
    border: 1px solid #d7dee2;
    border-radius: 8px;
    color: #41515c;
    font-weight: 800;
    margin-top: 18px;
    padding: 16px 12px 12px 12px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
    color: #172026;
    background: #ffffff;
}

QLineEdit,
QSpinBox,
QDoubleSpinBox {
    background: #fbfcfc;
    border: 1px solid #c9d4d9;
    border-radius: 6px;
    padding: 7px 8px;
    selection-background-color: #176b5d;
    selection-color: #ffffff;
}

QLineEdit:focus,
QSpinBox:focus,
QDoubleSpinBox:focus {
    border-color: #176b5d;
    background: #ffffff;
}

QPushButton {
    background: #eef2f4;
    border: 1px solid #c8d1d6;
    border-radius: 6px;
    color: #172026;
    font-weight: 800;
    min-height: 32px;
    padding: 7px 12px;
}

QPushButton:hover {
    background: #e2e8ec;
    border-color: #bcc8ce;
}

QPushButton:pressed {
    background: #d6dde1;
}

QPushButton:disabled {
    background: #edf0f2;
    border-color: #d7dee2;
    color: #9aa7ad;
}

QPushButton#StartButton {
    background: #176b5d;
    border-color: #135b50;
    color: #ffffff;
}

QPushButton#StartButton:hover {
    background: #135b50;
}

QPushButton#StopButton {
    background: #ffe2df;
    border-color: #f4aaa4;
    color: #9f1f16;
}

QPushButton#StopButton:hover {
    background: #ffd2cc;
    border-color: #e98f86;
}

QPushButton#PauseButton {
    background: #e0f2fe;
    border-color: #bae6fd;
    color: #082f49;
}

QPushButton#PauseButton:hover {
    background: #bae6fd;
    border-color: #7dd3fc;
}

QPushButton#BrowseButton {
    background: #eef2f4;
}

QCheckBox {
    color: #172026;
    spacing: 8px;
    min-height: 26px;
}

QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #bcc8ce;
    border-radius: 4px;
    background: #fbfcfc;
}

QCheckBox::indicator:hover {
    border-color: #176b5d;
}

QCheckBox::indicator:checked {
    background: #176b5d;
    border-color: #135b50;
}

QLabel#CameraMeta {
    background: #eef2f4;
    border: 1px solid #d7dee2;
    border-radius: 6px;
    color: #41515c;
    font-weight: 700;
    padding: 6px 8px;
}

QLabel#PreviewSurface {
    background: #172026;
    border: 1px solid #bcc8ce;
    border-radius: 6px;
    color: #d6dde1;
    font-weight: 700;
}

QLabel#CardDivider {
    color: #687981;
    font-weight: 800;
    padding: 2px 0;
}

QWidget#CircularProgress {
    background: transparent;
}

QScrollBar:vertical {
    background: transparent;
    width: 12px;
    margin: 2px;
}

QScrollBar::handle:vertical {
    background: #c8d1d6;
    border-radius: 5px;
    min-height: 32px;
}

QScrollBar::handle:vertical:hover {
    background: #aab8bf;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: transparent;
    height: 12px;
    margin: 2px;
}

QScrollBar::handle:horizontal {
    background: #c8d1d6;
    border-radius: 5px;
    min-width: 32px;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0;
}
"""

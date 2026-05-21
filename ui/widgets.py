"""自訂UI組件"""
from PySide6.QtWidgets import QLabel, QWidget, QSizePolicy
from PySide6.QtGui import QPainter, QColor
from PySide6.QtCore import Qt, QSize
from core.config import (
    CIRCULAR_PROGRESS_SIZE,
    PHOTO_PROGRESS_COLOR,
    COUNTDOWN_PROGRESS_COLOR,
    BACKGROUND_COLOR,
    INNER_CIRCLE_COLOR,
)


class AspectRatioLabel(QLabel):
    """保持寬高比的標籤"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return int(width * 9 / 16)


class CircularProgressWidget(QWidget):
    """圓形進度顯示組件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.photo_progress = 0.0
        self.countdown_progress = 0.0
        self.photo_text = "拍攝 0/0"
        self.countdown_text = "倒數 0s"

    def setPhotoProgress(self, current, total):
        self.photo_progress = 0.0
        if total > 0:
            self.photo_progress = min(max(current / total, 0.0), 1.0)
        self.update()

    def setCountdown(self, remaining, total):
        self.countdown_progress = 0.0
        if total > 0:
            self.countdown_progress = min(max((total - remaining) / total, 0.0), 1.0)
        self.update()

    def setStatusText(self, photo_text, countdown_text):
        self.photo_text = photo_text
        self.countdown_text = countdown_text
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        rect = self.rect().adjusted(10, 10, -10, -10)

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(*BACKGROUND_COLOR))
        painter.drawEllipse(rect)

        start_angle = 90 * 16
        if self.photo_progress > 0:
            painter.setBrush(QColor(*PHOTO_PROGRESS_COLOR))
            painter.drawPie(rect, start_angle, int(-360 * self.photo_progress * 16))

        inner = rect.adjusted(24, 24, -24, -24)
        painter.setBrush(QColor(*INNER_CIRCLE_COLOR))
        painter.drawEllipse(inner)

        if self.countdown_progress > 0:
            painter.setBrush(QColor(*COUNTDOWN_PROGRESS_COLOR))
            painter.drawPie(inner, start_angle, int(-360 * self.countdown_progress * 16))

        painter.setPen(QColor(0, 0, 0))
        painter.setBrush(Qt.NoBrush)
        painter.drawText(inner, Qt.AlignCenter, f"{self.photo_text}\n{self.countdown_text}")

    def sizeHint(self):
        return QSize(CIRCULAR_PROGRESS_SIZE, CIRCULAR_PROGRESS_SIZE)

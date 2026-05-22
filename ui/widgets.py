"""自訂UI組件"""
from PySide6.QtWidgets import QLabel, QWidget, QSizePolicy, QGroupBox, QVBoxLayout
from PySide6.QtGui import QPainter, QColor, QPixmap, QImage
from PySide6.QtCore import Qt, QSize
from core.config import (
    CIRCULAR_PROGRESS_SIZE,
    PHOTO_PROGRESS_COLOR,
    COUNTDOWN_PROGRESS_COLOR,
    BACKGROUND_COLOR,
    INNER_CIRCLE_COLOR,
    PREVIEW_MIN_WIDTH,
    PREVIEW_MIN_HEIGHT,
    CARD_LAST_PHOTO_LABEL,
)


class AspectRatioLabel(QLabel):
    """保持寬高比的標籤"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aspect_ratio = 16 / 9
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return int(width / self.aspect_ratio)

    def setAspectRatio(self, width: int, height: int) -> None:
        if width > 0 and height > 0:
            self.aspect_ratio = width / height
            self.updateGeometry()


class CameraCard(QWidget):
    """單台相機的預覽卡片，包含即時預覽與最後拍攝照片"""
    def __init__(self, camera_index: int, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.max_camera_size = None
        self._last_original_size = None

        group = QGroupBox(f"相機 {camera_index}")
        inner_layout = QVBoxLayout(group)

        self.size_label = QLabel("原始: 等待影像 | 最高: 偵測中")
        self.size_label.setAlignment(Qt.AlignCenter)

        self.preview_label = AspectRatioLabel(f"相機 {camera_index} 預覽")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(PREVIEW_MIN_WIDTH, PREVIEW_MIN_HEIGHT)

        separator = QLabel(CARD_LAST_PHOTO_LABEL)
        separator.setAlignment(Qt.AlignCenter)

        self.last_photo_label = AspectRatioLabel(f"相機 {camera_index} 最後拍攝")
        self.last_photo_label.setAlignment(Qt.AlignCenter)
        self.last_photo_label.setMinimumSize(PREVIEW_MIN_WIDTH, PREVIEW_MIN_HEIGHT)

        inner_layout.addWidget(self.size_label)
        inner_layout.addWidget(self.preview_label)
        inner_layout.addWidget(separator)
        inner_layout.addWidget(self.last_photo_label)

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(group)

    def update_preview(self, image: QImage) -> None:
        self.preview_label.setAspectRatio(image.width(), image.height())
        pixmap = QPixmap.fromImage(image)
        self.preview_label.setPixmap(
            pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio, Qt.FastTransformation)
        )

    def set_preview_waiting(self) -> None:
        self._last_original_size = None
        self.max_camera_size = None
        self.preview_label.clear()
        self.preview_label.setText(f"相機 {self.camera_index} 預覽")
        self.size_label.setText("原始: 等待影像 | 最高: 偵測中")

    def set_preview_inactive(self) -> None:
        self._last_original_size = None
        self.max_camera_size = None
        self.preview_label.clear()
        self.preview_label.setText(f"相機 {self.camera_index} 已關閉")
        self.size_label.setText("原始: 已關閉 | 最高: 未偵測")

    def _refresh_size_label(self) -> None:
        orig = self._last_original_size
        orig_text = f"{orig[0]}x{orig[1]}" if orig else "等待影像"
        max_size = self.max_camera_size
        max_text = f"{max_size[0]}x{max_size[1]}" if max_size else "偵測中"
        self.size_label.setText(f"原始: {orig_text} | 最高: {max_text}")

    def update_original_size(self, width: int, height: int) -> None:
        if self._last_original_size == (width, height):
            return
        self._last_original_size = (width, height)
        self._refresh_size_label()

    def set_max_camera_size(self, size) -> None:
        self.max_camera_size = size
        self._refresh_size_label()

    def update_last_photo(self, pixmap: QPixmap) -> None:
        self.last_photo_label.setPixmap(
            pixmap.scaled(self.last_photo_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def clear_last_photo(self) -> None:
        self.last_photo_label.clear()
        self.last_photo_label.setText(f"相機 {self.camera_index} 最後拍攝")


class CircularProgressWidget(QWidget):
    """圓形進度顯示組件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.photo_progress = 0.0
        self.countdown_progress = 0.0
        self.photo_text = "拍攝 0/0"
        self.countdown_text = "倒數 0s"
        self._color_bg = QColor(*BACKGROUND_COLOR)
        self._color_photo = QColor(*PHOTO_PROGRESS_COLOR)
        self._color_inner = QColor(*INNER_CIRCLE_COLOR)
        self._color_countdown = QColor(*COUNTDOWN_PROGRESS_COLOR)
        self._color_text = QColor(0, 0, 0)

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
        painter.setBrush(self._color_bg)
        painter.drawEllipse(rect)

        start_angle = 90 * 16
        if self.photo_progress > 0:
            painter.setBrush(self._color_photo)
            painter.drawPie(rect, start_angle, int(-360 * self.photo_progress * 16))

        inner = rect.adjusted(24, 24, -24, -24)
        painter.setBrush(self._color_inner)
        painter.drawEllipse(inner)

        if self.countdown_progress > 0:
            painter.setBrush(self._color_countdown)
            painter.drawPie(inner, start_angle, int(-360 * self.countdown_progress * 16))

        painter.setPen(self._color_text)
        painter.setBrush(Qt.NoBrush)
        painter.drawText(inner, Qt.AlignCenter, f"{self.photo_text}\n{self.countdown_text}")

    def sizeHint(self):
        return QSize(CIRCULAR_PROGRESS_SIZE, CIRCULAR_PROGRESS_SIZE)

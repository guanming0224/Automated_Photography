"""主窗口邏輯模組"""
import os
import cv2
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QSpinBox, QFileDialog, QSplitter,
    QGroupBox, QFormLayout, QCheckBox, QMessageBox,
    QScrollArea, QGridLayout,
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QTimer, Qt

from core.camera import CameraThread, find_available_cameras
from core.config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, CONTROL_PANEL_WIDTH, PREVIEW_PANEL_WIDTH,
    MAX_CAMERAS, DEFAULT_PHOTO_COUNT, DEFAULT_INTERVAL,
    MIN_PHOTO_COUNT, MAX_PHOTO_COUNT, MIN_INTERVAL, MAX_INTERVAL,
    DEFAULT_NAME_TEMPLATE, PREVIEW_GRID_COLUMNS,
)
from ui.widgets import CameraCard, CircularProgressWidget


class AutoCameraGUI(QMainWindow):
    """自動拍照GUI主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("自動拍照GUI")
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)

        self.cameras = find_available_cameras(MAX_CAMERAS)
        self.camera_threads = []
        self.camera_threads_by_index = {}
        self.camera_cards: dict[int, CameraCard] = {}
        self.camera_checkboxes = []
        self.selected_cameras = []
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.current_cycle = 0
        self.total_cycles = 0
        self.total_photos = 0
        self.saved_photos = 0
        self.interval = 0
        self.countdown_value = 0
        self.is_paused = False
        self.is_running = False
        self.save_path = ""
        self.name_template = DEFAULT_NAME_TEMPLATE

        self.init_ui()

    def init_ui(self):
        """初始化UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        control_scroll = self.create_control_panel()
        preview_scroll = self.create_preview_panel()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(control_scroll)
        splitter.addWidget(preview_scroll)
        splitter.setSizes([CONTROL_PANEL_WIDTH, PREVIEW_PANEL_WIDTH])

        main_layout.addWidget(splitter)
        self.start_camera_previews()

    def create_control_panel(self):
        """創建控制面板，包裹在 QScrollArea 中"""
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)

        # 存檔設定
        save_group = QGroupBox("存檔設定")
        save_layout = QFormLayout(save_group)
        self.save_path_edit = QLineEdit()
        self.save_path_edit.setText(os.getcwd())
        save_button = QPushButton("選擇資料夾")
        save_button.clicked.connect(self.select_save_path)
        path_row = QHBoxLayout()
        path_row.addWidget(self.save_path_edit)
        path_row.addWidget(save_button)
        save_layout.addRow("存檔位置:", path_row)
        self.name_edit = QLineEdit(DEFAULT_NAME_TEMPLATE)
        save_layout.addRow("命名模板\n(可用 {camera}、{index:04d}):", self.name_edit)
        control_layout.addWidget(save_group)

        # 拍攝設定
        capture_group = QGroupBox("拍攝設定")
        capture_layout = QFormLayout(capture_group)
        self.photo_count_spin = QSpinBox()
        self.photo_count_spin.setRange(MIN_PHOTO_COUNT, MAX_PHOTO_COUNT)
        self.photo_count_spin.setValue(DEFAULT_PHOTO_COUNT)
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(MIN_INTERVAL, MAX_INTERVAL)
        self.interval_spin.setValue(DEFAULT_INTERVAL)
        capture_layout.addRow("每台照片張數:", self.photo_count_spin)
        capture_layout.addRow("間隔時間 (秒):", self.interval_spin)
        control_layout.addWidget(capture_group)

        # 相機選擇
        camera_group = QGroupBox("相機選擇")
        camera_layout = QVBoxLayout(camera_group)
        if self.cameras:
            for cam in self.cameras:
                checkbox = QCheckBox(f"相機 {cam}")
                checkbox.setChecked(True)
                camera_layout.addWidget(checkbox)
                self.camera_checkboxes.append((cam, checkbox))
        else:
            camera_layout.addWidget(QLabel("未找到相機設備"))
        control_layout.addWidget(camera_group)

        # 拍攝控制按鈕群組
        button_group = QGroupBox("拍攝控制")
        button_layout = QVBoxLayout(button_group)
        start_stop_row = QHBoxLayout()
        self.start_button = QPushButton("開始拍攝")
        self.start_button.clicked.connect(self.start_capture)
        self.stop_button = QPushButton("結束拍攝")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_capture)
        start_stop_row.addWidget(self.start_button)
        start_stop_row.addWidget(self.stop_button)
        self.pause_button = QPushButton("暫停拍攝")
        self.pause_button.setEnabled(False)
        self.pause_button.clicked.connect(self.toggle_pause)
        button_layout.addLayout(start_stop_row)
        button_layout.addWidget(self.pause_button)
        control_layout.addWidget(button_group)

        # 圓形進度
        self.circular_progress = CircularProgressWidget()
        control_layout.addWidget(self.circular_progress, alignment=Qt.AlignCenter)

        control_layout.addStretch()

        scroll = QScrollArea()
        scroll.setWidget(control_panel)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        return scroll

    def create_preview_panel(self):
        """創建預覽面板：2欄 Grid 的 CameraCard，包裹在 QScrollArea 中"""
        container = QWidget()
        grid = QGridLayout(container)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        for i, cam in enumerate(self.cameras):
            card = CameraCard(cam)
            row, col = divmod(i, PREVIEW_GRID_COLUMNS)
            grid.addWidget(card, row, col)
            self.camera_cards[cam] = card

        scroll = QScrollArea()
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        return scroll

    def select_save_path(self):
        path = QFileDialog.getExistingDirectory(self, "選擇存檔資料夾")
        if path:
            self.save_path_edit.setText(path)

    def start_camera_previews(self):
        """啟動相機預覽線程"""
        for cam_idx in self.cameras:
            thread = CameraThread(cam_idx)
            thread.frame_ready.connect(self._dispatch_preview)
            thread.start()
            self.camera_threads.append(thread)
            self.camera_threads_by_index[cam_idx] = thread

    def _dispatch_preview(self, camera_index: int, image: QImage):
        """將 frame_ready 訊號轉發到對應的 CameraCard"""
        card = self.camera_cards.get(camera_index)
        if card:
            card.update_preview(image)

    def start_capture(self):
        """開始拍攝"""
        self.selected_cameras = [cam for cam, cb in self.camera_checkboxes if cb.isChecked()]
        if not self.selected_cameras:
            QMessageBox.warning(self, "相機未選擇", "請先勾選至少一台相機。")
            return

        self.save_path = self.save_path_edit.text()
        if not self.save_path or not os.path.isdir(self.save_path):
            QMessageBox.warning(self, "存檔路徑錯誤", "請選擇有效的存檔資料夾。")
            return

        for cam in self.selected_cameras:
            if cam in self.camera_cards:
                self.camera_cards[cam].clear_last_photo()

        self.name_template = self.name_edit.text().strip()
        self.total_cycles = self.photo_count_spin.value()
        self.interval = self.interval_spin.value()
        self.current_cycle = 0
        self.saved_photos = 0
        self.total_photos = self.total_cycles * len(self.selected_cameras)
        self.is_running = True
        self.is_paused = False
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.pause_button.setEnabled(True)
        self.pause_button.setText("暫停拍攝")
        self.countdown_value = self.interval
        self.circular_progress.setCountdown(self.countdown_value, self.interval)
        self.circular_progress.setPhotoProgress(self.saved_photos, self.total_photos)
        self.circular_progress.setStatusText(
            f"拍攝 {self.saved_photos}/{self.total_photos}",
            f"倒數 {self.countdown_value}s"
        )
        self.countdown_timer.start(1000)

    def update_countdown(self):
        """更新倒數計時"""
        if self.is_paused:
            return
        self.countdown_value -= 1
        self.circular_progress.setCountdown(self.countdown_value, self.interval)
        self.circular_progress.setStatusText(
            f"拍攝 {self.saved_photos}/{self.total_photos}",
            f"倒數 {self.countdown_value}s"
        )
        if self.countdown_value <= 0:
            self.countdown_timer.stop()
            self.capture_photo()

    def toggle_pause(self):
        """切換暫停/繼續"""
        if not self.is_running:
            return
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.countdown_timer.stop()
            self.pause_button.setText("繼續拍攝")
            self.circular_progress.setStatusText(
                f"拍攝 {self.saved_photos}/{self.total_photos}", "已暫停"
            )
        else:
            self.pause_button.setText("暫停拍攝")
            if self.countdown_value > 0:
                self.circular_progress.setStatusText(
                    f"拍攝 {self.saved_photos}/{self.total_photos}",
                    f"倒數 {self.countdown_value}s"
                )
                self.countdown_timer.start(1000)
            else:
                self.capture_photo()

    def stop_capture(self):
        """結束拍攝"""
        self.countdown_timer.stop()
        self.is_paused = False
        self.is_running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.pause_button.setText("暫停拍攝")
        self.circular_progress.setStatusText("已結束", "")

    def capture_photo(self):
        """拍攝照片"""
        if self.current_cycle >= self.total_cycles:
            self.finish_capture()
            return

        self.current_cycle += 1
        for cam in self.selected_cameras:
            thread = self.camera_threads_by_index.get(cam)
            frame = thread.get_latest_frame() if thread is not None else None
            if frame is None:
                continue

            cropped = CameraThread.crop_to_aspect(frame, 16, 9)
            try:
                filename = self.name_template.format(camera=cam, index=self.current_cycle)
            except Exception:
                filename = f"cam{cam}_{self.current_cycle:04d}.jpg"

            filepath = os.path.join(self.save_path, filename)
            cv2.imwrite(filepath, cropped)
            self.saved_photos += 1

            rgb_image = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb_image.shape
            qt_image = QImage(rgb_image.data, w, h, ch * w, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image)
            if cam in self.camera_cards:
                self.camera_cards[cam].update_last_photo(pixmap)

        self.circular_progress.setPhotoProgress(self.saved_photos, self.total_photos)
        self.circular_progress.setStatusText(
            f"拍攝 {self.saved_photos}/{self.total_photos}", "倒數 0s"
        )

        if self.current_cycle < self.total_cycles:
            self.countdown_value = self.interval
            self.circular_progress.setCountdown(self.countdown_value, self.interval)
            self.circular_progress.setStatusText(
                f"拍攝 {self.saved_photos}/{self.total_photos}",
                f"倒數 {self.countdown_value}s"
            )
            self.countdown_timer.start(1000)
        else:
            self.finish_capture()

    def finish_capture(self):
        """完成拍攝"""
        self.countdown_timer.stop()
        self.is_running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.pause_button.setText("暫停拍攝")
        self.circular_progress.setStatusText("拍攝完成", "")

    def closeEvent(self, event):
        """關閉事件"""
        self.countdown_timer.stop()
        for thread in self.camera_threads:
            thread.stop()
            thread.wait()
        event.accept()

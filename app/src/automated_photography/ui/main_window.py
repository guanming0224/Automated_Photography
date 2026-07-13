"""主窗口邏輯模組"""
import os
import cv2
import re
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox, QFileDialog, QSplitter,
    QGroupBox, QFormLayout, QCheckBox, QMessageBox,
    QScrollArea, QGridLayout, QFrame,
)
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import QThread, QTimer, Qt, Signal

from automated_photography.core.camera import CameraThread, find_available_cameras
from automated_photography.core.config import (
    WINDOW_WIDTH, WINDOW_HEIGHT, CONTROL_PANEL_WIDTH, PREVIEW_PANEL_WIDTH,
    MAX_CAMERAS, DEFAULT_PHOTO_COUNT, DEFAULT_INTERVAL,
    MIN_PHOTO_COUNT, MAX_PHOTO_COUNT, MIN_INTERVAL, MAX_INTERVAL,
    DEFAULT_NAME_TEMPLATE, DEFAULT_SAVE_DIR, PREVIEW_GRID_COLUMNS, CAPTURE_TIMEOUT_MS,
    INTERVAL_STEP, COUNTDOWN_TICK_MS,
)
from automated_photography.ui.widgets import CameraCard, CircularProgressWidget


class CameraDetectThread(QThread):
    cameras_found = Signal(list)

    def __init__(self, max_cameras, parent=None):
        super().__init__(parent)
        self.max_cameras = max_cameras

    def run(self):
        self.cameras_found.emit(find_available_cameras(self.max_cameras))


class SaveBatchThread(QThread):
    save_finished = Signal(int, list, list)

    def __init__(self, capture_id, items, parent=None):
        super().__init__(parent)
        self.capture_id = capture_id
        self.items = items

    def run(self):
        successes = []
        errors = []
        reserved_paths = set()
        for item in self.items:
            frame = item["frame"]
            path = self._resolve_path(
                item["name_template"], item["camera"], item["photo_index"],
                item["save_dir"], reserved_paths,
            )
            reserved_paths.add(path)
            ok = cv2.imwrite(path, frame)
            if ok:
                h, w = frame.shape[:2]
                thumb = cv2.resize(frame, (640, int(h * 640 / w)), interpolation=cv2.INTER_AREA) if w > 640 else frame
                successes.append({
                    "camera": item["camera"],
                    "thumbnail_rgb": cv2.cvtColor(thumb, cv2.COLOR_BGR2RGB),
                })
            else:
                errors.append(f"相機 {item['camera']} 存檔失敗：{path}")
        self.save_finished.emit(self.capture_id, successes, errors)

    @staticmethod
    def _resolve_path(name_template, camera_index, photo_index, save_dir, reserved_paths):
        try:
            filename = name_template.format(camera=camera_index, index=photo_index)
        except Exception:
            filename = f"cam{camera_index}_{photo_index:04d}.jpg"
        filename = os.path.basename(filename.strip())
        filename = re.sub(r'[<>:"/\\|?*]', "_", filename)
        if not filename:
            filename = f"cam{camera_index}_{photo_index:04d}.jpg"
        root, ext = os.path.splitext(filename)
        if not ext:
            ext = ".jpg"
        path = os.path.join(save_dir, root + ext)
        suffix = 1
        while path in reserved_paths or os.path.exists(path):
            path = os.path.join(save_dir, f"{root}_{suffix:03d}{ext}")
            suffix += 1
        return path


class AutoCameraGUI(QMainWindow):
    """自動拍照GUI主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("自動拍照GUI")
        self.setGeometry(100, 100, WINDOW_WIDTH, WINDOW_HEIGHT)

        self.cameras = []
        self.detect_thread = None
        self.camera_threads_by_index = {}
        self.camera_cards: dict[int, CameraCard] = {}
        self.camera_max_resolutions = {}
        self.camera_checkboxes = []
        self.selected_cameras = []
        self.countdown_timer = QTimer()
        self.countdown_timer.timeout.connect(self.update_countdown)
        self.capture_timeout_timer = QTimer()
        self.capture_timeout_timer.setSingleShot(True)
        self.capture_timeout_timer.timeout.connect(self._handle_capture_timeout)
        self.current_cycle = 0
        self.total_cycles = 0
        self.total_photos = 0
        self.saved_photos = 0
        self.capture_sequence = 0
        self.pending_capture_id = None
        self.pending_capture_results = {}
        self.pending_capture_expected = set()
        self.save_threads = []
        self.interval = 0
        self.countdown_value = 0
        self.is_paused = False
        self.is_running = False
        self.save_path = ""
        self.name_template = DEFAULT_NAME_TEMPLATE

        self.init_ui()
        self._detect_cameras()

    def init_ui(self):
        """初始化UI"""
        central_widget = QWidget()
        central_widget.setObjectName("AppRoot")
        central_widget.setAttribute(Qt.WA_StyledBackground, True)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        main_layout.addWidget(self.create_header())
        control_scroll = self.create_control_panel()
        preview_scroll = self.create_preview_panel()

        splitter = QSplitter(Qt.Horizontal)
        splitter.setObjectName("MainSplitter")
        splitter.addWidget(control_scroll)
        splitter.addWidget(preview_scroll)
        splitter.setSizes([CONTROL_PANEL_WIDTH, PREVIEW_PANEL_WIDTH])

        main_layout.addWidget(splitter, 1)

    def create_header(self):
        """建立頂部工作台狀態列"""
        header = QFrame()
        header.setObjectName("HeaderBar")
        header.setFrameShape(QFrame.Shape.NoFrame)

        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(12)

        title_layout = QVBoxLayout()
        title_layout.setContentsMargins(0, 0, 0, 0)
        title_layout.setSpacing(2)

        title = QLabel("自動拍照控制台")
        title.setObjectName("AppTitle")
        subtitle = QLabel("多相機影像擷取作業")
        subtitle.setObjectName("AppSubtitle")

        title_layout.addWidget(title)
        title_layout.addWidget(subtitle)
        header_layout.addLayout(title_layout, 1)

        self.header_status_label = QLabel("相機偵測中")
        self.header_status_label.setObjectName("HeaderBadge")
        self.header_status_label.setProperty("status", "neutral")
        self.header_status_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(self.header_status_label, 0, Qt.AlignRight | Qt.AlignVCenter)

        return header

    def _set_header_status(self, text: str, status: str = "neutral"):
        if not hasattr(self, "header_status_label"):
            return
        self.header_status_label.setText(text)
        self.header_status_label.setProperty("status", status)
        self.header_status_label.style().unpolish(self.header_status_label)
        self.header_status_label.style().polish(self.header_status_label)

    def _refresh_camera_status_badge(self):
        if not self.cameras:
            self._set_header_status("未找到相機", "warning")
            return

        active_count = sum(1 for _, checkbox in self.camera_checkboxes if checkbox.isChecked())
        if active_count:
            self._set_header_status(f"啟用 {active_count}/{len(self.cameras)} 台相機", "success")
        else:
            self._set_header_status("未啟用相機", "warning")

    def create_control_panel(self):
        """創建控制面板，包裹在 QScrollArea 中"""
        control_panel = QWidget()
        control_panel.setObjectName("ControlPanel")
        control_panel.setAttribute(Qt.WA_StyledBackground, True)
        control_layout = QVBoxLayout(control_panel)
        control_layout.setContentsMargins(0, 0, 10, 0)
        control_layout.setSpacing(12)

        # 存檔設定
        save_group = QGroupBox("存檔設定")
        save_layout = QFormLayout(save_group)
        save_layout.setHorizontalSpacing(10)
        save_layout.setVerticalSpacing(12)
        self.save_path_edit = QLineEdit()
        default_save_path = os.path.join(os.path.expanduser("~"), "Desktop", DEFAULT_SAVE_DIR)
        os.makedirs(default_save_path, exist_ok=True)
        self.save_path_edit.setText(default_save_path)
        save_button = QPushButton("選擇資料夾")
        save_button.setObjectName("BrowseButton")
        save_button.clicked.connect(self.select_save_path)
        path_row = QHBoxLayout()
        path_row.setSpacing(8)
        path_row.addWidget(self.save_path_edit)
        path_row.addWidget(save_button)
        save_layout.addRow("存檔位置:", path_row)
        self.name_edit = QLineEdit(DEFAULT_NAME_TEMPLATE)
        save_layout.addRow("命名模板\n(可用 {camera}、{index:04d}):", self.name_edit)
        control_layout.addWidget(save_group)

        # 拍攝設定
        capture_group = QGroupBox("拍攝設定")
        capture_layout = QFormLayout(capture_group)
        capture_layout.setHorizontalSpacing(10)
        capture_layout.setVerticalSpacing(12)
        self.photo_count_spin = QSpinBox()
        self.photo_count_spin.setRange(MIN_PHOTO_COUNT, MAX_PHOTO_COUNT)
        self.photo_count_spin.setValue(DEFAULT_PHOTO_COUNT)
        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(MIN_INTERVAL, MAX_INTERVAL)
        self.interval_spin.setDecimals(2)
        self.interval_spin.setSingleStep(INTERVAL_STEP)
        self.interval_spin.setSuffix(" s")
        self.interval_spin.setValue(DEFAULT_INTERVAL)
        capture_layout.addRow("每台照片張數:", self.photo_count_spin)
        capture_layout.addRow("間隔時間 (秒):", self.interval_spin)

        capture_layout.addRow("輸出尺寸:", QLabel("使用相機原始 frame"))
        control_layout.addWidget(capture_group)

        # 相機選擇
        camera_group = QGroupBox("相機選擇")
        self.camera_layout = QVBoxLayout(camera_group)
        self.camera_layout.setSpacing(8)
        self.detecting_label = QLabel("偵測相機中...")
        self.detecting_label.setObjectName("MutedLabel")
        self.camera_layout.addWidget(self.detecting_label)
        control_layout.addWidget(camera_group)

        # 拍攝控制按鈕群組
        button_group = QGroupBox("拍攝控制")
        button_layout = QVBoxLayout(button_group)
        button_layout.setSpacing(8)
        start_stop_row = QHBoxLayout()
        start_stop_row.setSpacing(8)
        self.start_button = QPushButton("開始拍攝")
        self.start_button.setObjectName("StartButton")
        self.start_button.clicked.connect(self.start_capture)
        self.stop_button = QPushButton("結束拍攝")
        self.stop_button.setObjectName("StopButton")
        self.stop_button.setEnabled(False)
        self.stop_button.clicked.connect(self.stop_capture)
        start_stop_row.addWidget(self.start_button)
        start_stop_row.addWidget(self.stop_button)
        self.pause_button = QPushButton("暫停拍攝")
        self.pause_button.setObjectName("PauseButton")
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
        scroll.setObjectName("ControlScroll")
        scroll.setWidget(control_panel)
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        return scroll

    def create_preview_panel(self):
        """創建預覽面板：2欄 Grid 的 CameraCard，包裹在 QScrollArea 中"""
        container = QWidget()
        container.setObjectName("PreviewPanel")
        container.setAttribute(Qt.WA_StyledBackground, True)
        self.preview_grid = QGridLayout(container)
        self.preview_grid.setContentsMargins(0, 0, 0, 0)
        self.preview_grid.setHorizontalSpacing(12)
        self.preview_grid.setVerticalSpacing(12)
        self.preview_grid.setColumnStretch(0, 1)
        self.preview_grid.setColumnStretch(1, 1)

        scroll = QScrollArea()
        scroll.setObjectName("PreviewScroll")
        scroll.setWidget(container)
        scroll.setWidgetResizable(True)
        return scroll

    def select_save_path(self):
        path = QFileDialog.getExistingDirectory(self, "選擇存檔資料夾")
        if path:
            self.save_path_edit.setText(path)

    def _detect_cameras(self):
        self.detect_thread = CameraDetectThread(MAX_CAMERAS, self)
        self.detect_thread.cameras_found.connect(self._on_cameras_found)
        self.detect_thread.start()

    def _on_cameras_found(self, cameras):
        self.cameras = cameras
        self.detecting_label.hide()
        if not cameras:
            no_camera_label = QLabel("未找到相機設備")
            no_camera_label.setObjectName("MutedLabel")
            self.camera_layout.addWidget(no_camera_label)
            self._refresh_camera_status_badge()
            return
        for cam in cameras:
            checkbox = QCheckBox(f"相機 {cam}")
            checkbox.setChecked(True)
            checkbox.toggled.connect(lambda checked, cam=cam: self._on_camera_checkbox_changed(cam, checked))
            self.camera_layout.addWidget(checkbox)
            self.camera_checkboxes.append((cam, checkbox))
        for i, cam in enumerate(cameras):
            card = CameraCard(cam)
            row, col = divmod(i, PREVIEW_GRID_COLUMNS)
            self.preview_grid.addWidget(card, row, col)
            self.camera_cards[cam] = card
        self._refresh_camera_status_badge()
        self.start_camera_previews()

    def start_camera_previews(self):
        """啟動相機預覽線程"""
        for cam_idx, checkbox in self.camera_checkboxes:
            if checkbox.isChecked():
                self.start_camera_preview(cam_idx)

    def start_camera_preview(self, cam_idx):
        """啟動單台相機預覽並占用硬體資源。"""
        if cam_idx in self.camera_threads_by_index:
            return

        card = self.camera_cards.get(cam_idx)
        if card:
            card.set_preview_waiting()

        thread = CameraThread(cam_idx)
        thread.frame_ready.connect(self._dispatch_preview)
        thread.capture_ready.connect(self._handle_capture_frame)
        thread.max_resolution_ready.connect(self._on_max_resolution_ready)
        thread.start()
        self.camera_threads_by_index[cam_idx] = thread

    def stop_camera_preview(self, cam_idx):
        """停止單台相機預覽並釋放硬體資源。"""
        thread = self.camera_threads_by_index.pop(cam_idx, None)
        if thread is not None:
            thread.stop()
            thread.wait()

        self.camera_max_resolutions.pop(cam_idx, None)
        self.selected_cameras = [cam for cam in self.selected_cameras if cam != cam_idx]

        if cam_idx in self.pending_capture_expected:
            self.pending_capture_expected.discard(cam_idx)
            self.pending_capture_results.pop(cam_idx, None)
            if self.pending_capture_id is not None and set(self.pending_capture_results) >= self.pending_capture_expected:
                self._finalize_pending_capture([f"相機 {cam_idx} 已關閉，略過本輪拍攝。"])

        card = self.camera_cards.get(cam_idx)
        if card:
            card.set_preview_inactive()

    def _on_camera_checkbox_changed(self, cam_idx, checked):
        """左側相機勾選狀態就是右側預覽與硬體串流開關。"""
        if checked:
            self.start_camera_preview(cam_idx)
        else:
            self.stop_camera_preview(cam_idx)
        self._refresh_camera_status_badge()

    def _on_max_resolution_ready(self, camera_index: int, width: int, height: int):
        """相機執行緒完成最高解析度偵測後更新 Card"""
        if camera_index not in self.camera_threads_by_index:
            return
        size = (width, height)
        self.camera_max_resolutions[camera_index] = size
        card = self.camera_cards.get(camera_index)
        if card:
            card.set_max_camera_size(size)
            card.update_original_size(width, height)

    def _dispatch_preview(self, camera_index: int, image: QImage):
        """將 frame_ready 訊號轉發到對應的 CameraCard"""
        if camera_index not in self.camera_threads_by_index:
            return
        card = self.camera_cards.get(camera_index)
        if card:
            card.update_preview(image)

    @staticmethod
    def _format_seconds(value):
        value = max(float(value), 0.0)
        if value >= 10:
            return f"{value:.0f}s"
        if value >= 1:
            return f"{value:.1f}s"
        return f"{value:.2f}s"

    def start_capture(self):
        """開始拍攝"""
        for cam, cb in self.camera_checkboxes:
            if cb.isChecked() and cam not in self.camera_threads_by_index:
                self.start_camera_preview(cam)

        self.selected_cameras = [
            cam for cam, cb in self.camera_checkboxes
            if cb.isChecked() and cam in self.camera_threads_by_index
        ]
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
            f"倒數 {self._format_seconds(self.countdown_value)}"
        )
        self.countdown_timer.start(COUNTDOWN_TICK_MS)

    def update_countdown(self):
        """更新倒數計時"""
        if self.is_paused:
            return
        self.countdown_value -= COUNTDOWN_TICK_MS / 1000
        self.circular_progress.setCountdown(self.countdown_value, self.interval)
        self.circular_progress.setStatusText(
            f"拍攝 {self.saved_photos}/{self.total_photos}",
            f"倒數 {self._format_seconds(self.countdown_value)}"
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
                    f"倒數 {self._format_seconds(self.countdown_value)}"
                )
                self.countdown_timer.start(COUNTDOWN_TICK_MS)
            else:
                self.capture_photo()

    def stop_capture(self):
        """結束拍攝"""
        self.countdown_timer.stop()
        self.capture_timeout_timer.stop()
        self.pending_capture_id = None
        self.pending_capture_expected = set()
        self.pending_capture_results = {}
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
        self.capture_sequence += 1
        self.pending_capture_id = self.capture_sequence
        self.pending_capture_results = {}
        self.pending_capture_expected = set(self.selected_cameras)

        self.circular_progress.setStatusText(
            f"拍攝 {self.saved_photos}/{self.total_photos}",
            f"第 {self.current_cycle}/{self.total_cycles} 輪"
        )

        for cam in self.selected_cameras:
            thread = self.camera_threads_by_index.get(cam)
            if thread is None:
                self.pending_capture_expected.discard(cam)
                continue
            thread.request_capture(self.pending_capture_id)

        if not self.pending_capture_expected:
            self._finalize_pending_capture(["沒有可用的相機執行緒。"])
            return

        self.capture_timeout_timer.start(CAPTURE_TIMEOUT_MS)

    def _handle_capture_frame(self, camera_index, capture_id, frame, timestamp):
        if capture_id != self.pending_capture_id:
            return
        if camera_index not in self.pending_capture_expected:
            return

        self.pending_capture_results[camera_index] = {
            "frame": frame,
            "timestamp": timestamp,
        }

        if set(self.pending_capture_results) >= self.pending_capture_expected:
            self._finalize_pending_capture([])

    def _handle_capture_timeout(self):
        if self.pending_capture_id is None:
            return
        missing = sorted(self.pending_capture_expected - set(self.pending_capture_results))
        errors = [f"相機 {cam} 拍攝逾時。" for cam in missing]
        self._finalize_pending_capture(errors)

    def _finalize_pending_capture(self, errors):
        if self.pending_capture_id is None:
            return

        self.capture_timeout_timer.stop()
        capture_id = self.pending_capture_id
        capture_items = self._build_capture_items()

        self.pending_capture_id = None
        self.pending_capture_expected = set()
        self.pending_capture_results = {}

        if not capture_items:
            self._on_save_batch_finished(capture_id, [], errors)
            return

        save_thread = SaveBatchThread(capture_id, capture_items, self)
        save_thread.save_finished.connect(
            lambda finished_id, successes, save_errors, initial_errors=errors:
                self._on_save_batch_finished(
                    finished_id,
                    successes,
                    initial_errors + save_errors,
                )
        )
        save_thread.finished.connect(lambda thread=save_thread: self._remove_save_thread(thread))
        self.save_threads.append(save_thread)
        save_thread.start()

    def _build_capture_items(self):
        items = []
        for cam, result in sorted(self.pending_capture_results.items()):
            items.append({
                "camera": cam,
                "photo_index": self.current_cycle,
                "save_dir": self.save_path,
                "name_template": self.name_template,
                "frame": result["frame"],
            })
        return items

    def _on_save_batch_finished(self, capture_id, successes, errors):
        for item in successes:
            self.saved_photos += 1
            rgb = item["thumbnail_rgb"]
            h, w, ch = rgb.shape
            qt_image = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qt_image.copy())
            card = self.camera_cards.get(item["camera"])
            if card:
                card.update_last_photo(pixmap)

        self.circular_progress.setPhotoProgress(self.saved_photos, self.total_photos)

        if errors:
            QMessageBox.warning(self, "拍攝或存檔異常", "\n".join(errors[:8]))

        if not self.is_running:
            # 使用者已手動結束，不干擾現有狀態文字
            return

        if self.current_cycle < self.total_cycles:
            self.countdown_value = self.interval
            self.circular_progress.setCountdown(self.countdown_value, self.interval)
            self.circular_progress.setStatusText(
                f"拍攝 {self.saved_photos}/{self.total_photos}",
                f"倒數 {self._format_seconds(self.countdown_value)}"
            )
            self.countdown_timer.start(COUNTDOWN_TICK_MS)
        else:
            self.finish_capture()

    def _remove_save_thread(self, thread):
        if thread in self.save_threads:
            self.save_threads.remove(thread)

    def finish_capture(self):
        """完成拍攝"""
        self.countdown_timer.stop()
        self.capture_timeout_timer.stop()
        self.pending_capture_id = None
        self.pending_capture_expected = set()
        self.pending_capture_results = {}
        self.is_running = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.pause_button.setEnabled(False)
        self.pause_button.setText("暫停拍攝")
        self.circular_progress.setStatusText("拍攝完成", "")

    def closeEvent(self, event):
        """關閉事件"""
        self.countdown_timer.stop()
        self.capture_timeout_timer.stop()
        self.is_running = False
        if self.detect_thread and self.detect_thread.isRunning():
            self.detect_thread.wait(3000)
        for thread in list(self.camera_threads_by_index.values()):
            thread.stop()
            thread.wait(3000)
        for thread in list(self.save_threads):
            thread.wait(3000)
        event.accept()

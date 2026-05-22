"""相機控制模組"""
import cv2
import threading
import time
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
from core.config import COMMON_CAMERA_RESOLUTIONS


def open_camera(index):
    """開啟相機"""
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(index)
    return cap


class CameraThread(QThread):
    """相機取框線程"""
    frame_ready = Signal(int, QImage, int, int)
    capture_ready = Signal(int, int, object, float)
    max_resolution_ready = Signal(int, int, int)  # camera_index, max_w, max_h

    def __init__(self, camera_index):
        super().__init__()
        self.camera_index = camera_index
        self.cap = None
        self.running = False
        self._frame_lock = threading.Lock()
        self._latest_frame = None
        self._capture_lock = threading.Lock()
        self._pending_capture_ids = []

    def run(self):
        self.cap = open_camera(self.camera_index)
        if not self.cap.isOpened():
            self.cap.release()
            self.cap = None
            return
        max_w, max_h = self._probe_max_resolution()
        self.max_resolution_ready.emit(self.camera_index, max_w, max_h)

        self.running = True
        try:
            while self.running:
                ret, frame = self.cap.read()
                if ret and frame is not None:
                    original_h, original_w = frame.shape[:2]
                    frame_copy = frame.copy()
                    timestamp = time.time()
                    with self._frame_lock:
                        self._latest_frame = frame_copy

                    for capture_id in self._take_pending_capture_ids():
                        self.capture_ready.emit(
                            self.camera_index,
                            capture_id,
                            frame_copy.copy(),
                            timestamp,
                        )

                    rgb_image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                    h, w, ch = rgb_image.shape
                    bytes_per_line = ch * w
                    qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                    self.frame_ready.emit(
                        self.camera_index,
                        qt_image.copy(),
                        original_w,
                        original_h,
                    )
                self.msleep(30)
        finally:
            if self.cap:
                self.cap.release()
                self.cap = None

    def _probe_max_resolution(self):
        """在已開啟的 cap 上以 CAP_PROP 查詢最大支援解析度，不讀幀，速度快。"""
        cur_w = self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)
        cur_h = self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
        best_w, best_h = int(cur_w), int(cur_h)
        for width, height in COMMON_CAMERA_RESOLUTIONS:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            actual_w = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            actual_h = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            if actual_w * actual_h > best_w * best_h:
                best_w, best_h = actual_w, actual_h
            if actual_w == width and actual_h == height:
                break
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, best_w)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, best_h)
        return best_w, best_h

    def get_latest_frame(self):
        """執行緒安全地取得最新一幀的副本"""
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def stop(self):
        self.running = False
        with self._capture_lock:
            self._pending_capture_ids = []

    def request_capture(self, capture_id):
        """Ask the camera thread to return the next available frame."""
        with self._capture_lock:
            if capture_id not in self._pending_capture_ids:
                self._pending_capture_ids.append(capture_id)

    def _take_pending_capture_ids(self):
        with self._capture_lock:
            capture_ids = self._pending_capture_ids
            self._pending_capture_ids = []
        return capture_ids

def find_available_cameras(max_cameras=5):
    """尋找可用的相機設備"""
    cameras = []
    for i in range(max_cameras):
        cap = open_camera(i)
        if cap.isOpened():
            cameras.append(i)
            cap.release()
    return cameras



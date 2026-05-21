"""相機控制模組"""
import cv2
import threading
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage


def open_camera(index):
    """開啟相機"""
    cap = cv2.VideoCapture(index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap.release()
        cap = cv2.VideoCapture(index)
    return cap


class CameraThread(QThread):
    """相機取框線程"""
    frame_ready = Signal(int, QImage)

    def __init__(self, camera_index):
        super().__init__()
        self.camera_index = camera_index
        self.cap = None
        self.running = False
        self._frame_lock = threading.Lock()
        self._latest_frame = None

    def run(self):
        self.cap = open_camera(self.camera_index)
        if not self.cap.isOpened():
            return
        self.running = True
        while self.running:
            ret, frame = self.cap.read()
            if ret and frame is not None:
                with self._frame_lock:
                    self._latest_frame = frame.copy()
                cropped = self.crop_to_aspect(frame, 16, 9)
                rgb_image = cv2.cvtColor(cropped, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_image.shape
                bytes_per_line = ch * w
                qt_image = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
                self.frame_ready.emit(self.camera_index, qt_image)
            self.msleep(30)

    def get_latest_frame(self):
        """執行緒安全地取得最新一幀的副本"""
        with self._frame_lock:
            if self._latest_frame is None:
                return None
            return self._latest_frame.copy()

    def stop(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None

    @staticmethod
    def crop_to_aspect(frame, w_ratio, h_ratio):
        """裁切幀為指定寬高比"""
        h, w = frame.shape[:2]
        target = w_ratio / h_ratio
        current = w / h
        if current > target:
            new_w = int(target * h)
            x1 = (w - new_w) // 2
            return frame[:, x1:x1 + new_w]
        elif current < target:
            new_h = int(w / target)
            y1 = (h - new_h) // 2
            return frame[y1:y1 + new_h, :]
        return frame


def find_available_cameras(max_cameras=5):
    """尋找可用的相機設備"""
    cameras = []
    for i in range(max_cameras):
        cap = open_camera(i)
        if cap.isOpened():
            cameras.append(i)
            cap.release()
    return cameras

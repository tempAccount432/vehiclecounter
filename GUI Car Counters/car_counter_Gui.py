# Code with cv and video
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QImage
import cv2
import sys
import numpy as np
from ultralytics import YOLO
import cvzone
import math
from sort import Sort

class VideoThread(QThread):
    update_frame = Signal(QImage)

    def __init__(self):
        super().__init__()
        self.cap = None
        self.running = False
        self.paused = False
        self.model = YOLO("../Yolo-Weights/yolov8l.pt")
        self.tracker = Sort(max_age=20, min_hits=3, iou_threshold=0.3)
        self.classNames = ["person", "bicycle", "car", "motorbike", "aeroplane", "bus", "train", "truck", "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "sofa", "pottedplant", "bed", "diningtable", "toilet", "tvmonitor", "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"]
        self.totalCount = []
        self.limits = [400, 297, 673, 297]

    def set_video_source(self, video_path):
        self.cap = cv2.VideoCapture(video_path)

    def run(self):
        self.running = True
        while self.cap.isOpened() and self.running:
            if self.paused:
                continue
            ret, img = self.cap.read()
            if not ret:
                break
            results = self.model(img, stream=True)
            detections = np.empty((0, 5))
            for r in results:
                boxes = r.boxes
                for box in boxes:
                    x1, y1, x2, y2 = map(int, box.xyxy[0])
                    conf = float(box.conf[0])
                    cls = int(box.cls[0])
                    currentClass = self.classNames[cls]
                    if currentClass in ["car", "truck", "bus", "motorbike"] and conf > 0.3:
                        currentArray = np.array([x1, y1, x2, y2, conf])
                        detections = np.vstack((detections, currentArray))
            resultsTracker = self.tracker.update(detections)
            for result in resultsTracker:
                x1, y1, x2, y2, id = map(int, result)
                cx, cy = x1 + (x2 - x1) // 2, y1 + (y2 - y1) // 2
                if self.limits[0] < cx < self.limits[2] and self.limits[1] - 15 < cy < self.limits[1] + 15:
                    if id not in self.totalCount:
                        self.totalCount.append(id)
            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, ch = img.shape
            bytes_per_line = ch * w
            qimg = QImage(img.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.update_frame.emit(qimg)

    def pause(self):
        self.paused = not self.paused

    def stop(self):
        self.running = False
        self.quit()
        self.wait()

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Vehicle Detection System")
        self.setGeometry(100, 100, 1280, 720)
        self.setMinimumSize(684, 437)
        main_layout = QVBoxLayout()
        self.video_label = QLabel("No Video Selected")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setScaledContents(True)
        main_layout.addWidget(self.video_label)
        button_layout = QHBoxLayout()
        self.select_button = QPushButton("Select File")
        self.select_button.clicked.connect(self.select_file)
        button_layout.addWidget(self.select_button)
        self.play_pause_button = QPushButton("Play")
        self.play_pause_button.setCheckable(True)
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        button_layout.addWidget(self.play_pause_button)
        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.close)
        button_layout.addWidget(self.quit_button)
        main_layout.addLayout(button_layout)
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        self.video_thread = VideoThread()
        self.video_thread.update_frame.connect(self.display_frame)
        self.video_path = ""

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Videos (*.mp4 *.mov *.avi)")
        if file_path:
            self.video_path = file_path
            cap = cv2.VideoCapture(file_path)
            ret, frame = cap.read()
            cap.release()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = frame.shape
                bytes_per_line = ch * w
                qimg = QImage(frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
                pixmap = QPixmap.fromImage(qimg)
                self.video_label.setPixmap(pixmap)
                self.video_label.setScaledContents(True)
            else:
                self.video_label.setText("Failed to load thumbnail")

    def toggle_play_pause(self):
        if self.video_thread.isRunning():
            self.video_thread.pause()
            self.play_pause_button.setText("Play")
        else:
            if not self.video_thread.running:
                self.video_thread.set_video_source(self.video_path)
                self.video_thread.start()
            self.video_thread.pause()
            self.play_pause_button.setText("Pause")

    def display_frame(self, qimg):
        pixmap = QPixmap.fromImage(qimg)
        self.video_label.setPixmap(pixmap)
        self.video_label.setScaledContents(True)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

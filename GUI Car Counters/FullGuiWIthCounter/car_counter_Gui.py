# Code with cv and video
from PySide6.QtWidgets import QApplication, QMainWindow, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QMessageBox
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QImage, QIcon
import cv2
import sys
import numpy as np
from ultralytics import YOLO
import cvzone
import math
from sort import Sort
from single_instance import SingleInstance

class VideoThread(QThread):
    update_frame = Signal(QImage)
    # Global var for the video thread
    def __init__(self):
        super().__init__()
        self.cap = None
        self.running = False
        self.paused = False
        # self.frame_count = 0
        # self.frame_skip_threshold = 3
        self.model = YOLO("/Yolo-Weights/yolov8n.pt")
        self.mask = cv2.imread("assets/mask-1280-720.png")
        self.tracker = Sort(max_age=20, min_hits=3, iou_threshold=0.3)
        self.classNames = ["person", "bicycle", "car", "motorbike", "aeroplane", "bus", "train", "truck", "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "sofa", "pottedplant", "bed", "diningtable", "toilet", "tvmonitor", "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"]
        self.totalCount = []
        self.limits = [400, 297, 673, 297]

    def set_video_source(self, video_path):
        self.cap = cv2.VideoCapture(video_path)

    def run(self):
        self.running = True
        while self.cap.isOpened() and self.running:
            if self.paused: #probalby here is the problem
                continue
            ret, img = self.cap.read()
            if not ret:
                break
            imgRegion = cv2.bitwise_and(img, self.mask)
 
            imgGraphics = cv2.imread("assets/graphics.png", cv2.IMREAD_UNCHANGED)
            img = cvzone.overlayPNG(img, imgGraphics, (0, 0))
            results = self.model(imgRegion, stream=True)

            detections = np.empty((0, 5))

            for r in results:
                boxes = r.boxes
                for box in boxes:
                    # Bounding Box
                    x1, y1, x2, y2 = box.xyxy[0]
                    x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
                    # cv2.rectangle(img,(x1,y1),(x2,y2),(255,0,255),3)
                    w, h = x2 - x1, y2 - y1
        
                    # Confidence
                    conf = math.ceil((box.conf[0] * 100)) / 100
                    # Class Name
                    cls = int(box.cls[0])
                    currentClass = self.classNames[cls]
                    if currentClass in ["car", "truck", "bus", "motorbike"] and conf > 0.3:
                        # cvzone.putTextRect(img, f'{currentClass} {conf}', (max(0, x1), max(35, y1)), scale=0.6, thickness=1, offset=3)
                        # cvzone.cornerRect(img, (x1, y1, w, h), l=9, rt=5)
                        currentArray = np.array([x1, y1, x2, y2, conf])
                        detections = np.vstack((detections, currentArray))
            resultsTracker = self.tracker.update(detections)

            cv2.line(img, (self.limits[0], self.limits[1]), (self.limits[2], self.limits[3]), (0, 0, 255), 5)
            for result in resultsTracker:
                x1, y1, x2, y2, id = map(int, result)
                print(result)
                w, h = x2 - x1, y2 - y1
                cvzone.cornerRect(img, (x1, y1, w, h), l=9, rt=2, colorR=(255, 0, 255))
                cvzone.putTextRect(img, f' {int(id)}', (max(0, x1), max(35, y1)),
                scale=2, thickness=3, offset=10)

                cx, cy = x1 + w // 2, y1 + h // 2
                cv2.circle(img, (cx, cy), 5, (255, 0, 255), cv2.FILLED)

                if self.limits[0] < cx < self.limits[2] and self.limits[1] - 15 < cy < self.limits[1] + 15:
                    if id not in self.totalCount:
                        self.totalCount.append(id)
                        cv2.line(img, (self.limits[0], self.limits[1]), (self.limits[2], self.limits[3]), (0, 255, 0), 5)

            # cvzone.putTextRect(img, f' Count: {len(totalCount)}', (50, 50))
            cv2.putText(img,str(len(self.totalCount)),(255,100),cv2.FONT_HERSHEY_PLAIN,5,(50,50,255),8)

            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, ch = img.shape
            bytes_per_line = ch * w
            qimg = QImage(img.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.update_frame.emit(qimg)

    def pause(self):
        self.paused = not self.paused
        print(self.paused)

    def stop(self):
        if self.running:
            self.running = False
            self.quit()
            self.wait()

class MainWindow(QMainWindow):
    # Global var for the main window
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("assets/car_icon.ico"))
        self.setWindowTitle("Vehicle Detection System")
        self.setGeometry(100, 100, 1280, 720)
        self.setMinimumSize(684, 437)
        # Main Layout
        main_layout = QVBoxLayout()
        
        self.video_label = QLabel("No Video Selected")
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setScaledContents(True)  # Ensure scaling -- maybe I can remove this
        main_layout.addWidget(self.video_label)
        
        # Control Buttons Layout
        button_layout = QHBoxLayout()
        
        self.select_button = QPushButton("Select File")
        self.select_button.clicked.connect(self.select_file)
        button_layout.addWidget(self.select_button)

        self.play_pause_button = QPushButton("Play")
        self.play_pause_button.setCheckable(True) #i think here is the problem
        self.play_pause_button.clicked.connect(self.toggle_play_pause)
        button_layout.addWidget(self.play_pause_button)

        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.close)
        button_layout.addWidget(self.quit_button)
        
        main_layout.addLayout(button_layout)
        
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

        # Video Thread
        self.video_thread = VideoThread()
        self.video_thread.update_frame.connect(self.display_frame)
        self.video_path = ""
        self.is_playing = False

    def select_file(self):
        # Select the video file and sets the image
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Videos (*.mp4 *.mov *.avi)")
        if file_path:
            if self.is_playing:
                self.stop_video()
            self.video_path = file_path
            self.set_thumbnail(file_path)

    def set_thumbnail(self, file_path):
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

    # def toggle_play_pause(self):
    #     if self.video_thread.isRunning():
    #         self.video_thread.pause()
    #         self.play_pause_button.setText("Play")
    #     else:
    #         if not self.video_thread.running:
    #             self.video_thread.set_video_source(self.video_path)
    #             self.video_thread.start()
    #         self.video_thread.pause()
    #         self.play_pause_button.setText("Pause")

    def toggle_play_pause(self):
        if self.is_playing:
            self.stop_video()
            self.play_pause_button.setText("Play")
        else:
            self.start_video()
            self.play_pause_button.setText("Pause")

    def start_video(self):
        if self.video_path:
            self.video_thread.set_video_source(self.video_path)
            self.video_thread.start()
            self.is_playing = True
        else:
            self.video_label.setText("Please select a video first.")

    def stop_video(self):
        self.video_thread.stop()
        self.is_playing = False

    def closeEvent(self, event):
        reply = QMessageBox.question(
            self,
            "Close Confirmation",
            "Are you sure you want to close?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if reply == QMessageBox.Yes:
            self.stop_video()
            event.accept()
        else:
            event.ignore()

    def display_frame(self, qimg):
        pixmap = QPixmap.fromImage(qimg)
        self.video_label.setPixmap(pixmap)
        self.video_label.setScaledContents(True)

if __name__ == "__main__":
    instance_checker = SingleInstance()
    instance_checker.acquire()

    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())

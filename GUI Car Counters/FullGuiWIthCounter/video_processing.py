from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage
import cv2
import numpy as np
import cvzone
import math
from ultralytics import YOLO
from sort import Sort

class VideoThread(QThread):
    update_frame = Signal(QImage)
    # Global var for the video thread
    def __init__(self):
        super().__init__()
        self.cap = None
        self.running = False
        self.paused = False
        self.current_frame_pos = 0 
        # self.frame_count = 0
        # self.frame_skip_threshold = 3
        self.model = YOLO("/Yolo-Weights/yolov8n.pt")
        self.mask = None
        self.tracker = Sort(max_age=20, min_hits=3, iou_threshold=0.3)
        self.classNames = ["person", "bicycle", "car", "motorbike", "aeroplane", "bus", "train", "truck", "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "sofa", "pottedplant", "bed", "diningtable", "toilet", "tvmonitor", "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier", "toothbrush"]
        self.totalCount = []
        self.limits = [400, 297, 673, 297]

    def set_video_source(self, video_path):
        if self.cap:
            self.cap.release()
        self.cap = cv2.VideoCapture(video_path)
        self.current_frame_pos = 0

    def set_mask_source(self, mask_path):
        self.mask = cv2.imread(mask_path)

    def run(self):
        self.running = True
        self.paused = False

        # Resume from the last frame position
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)

        while self.cap.isOpened() and self.running:
            if self.paused:
                self.msleep(100)
                continue

            ret, img = self.cap.read()
            if not ret:
                break

            self.current_frame_pos = int(self.cap.get(cv2.CAP_PROP_POS_FRAMES))  # Store frame position

            if self.mask is not None:
                imgRegion = cv2.bitwise_and(img, self.mask)
            else:
                imgRegion = img 
 
            # Optional graphics overlay
            imgGraphics = cv2.imread("assets/graphics.png", cv2.IMREAD_UNCHANGED)
            if imgGraphics is not None:
                img = cvzone.overlayPNG(img, imgGraphics, (0, 0))

            # YOLO detection
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
             
            start_x, start_y, end_x, end_y = self.limits
            cv2.line(img, (start_x, start_y), (end_x,end_y), (0, 0, 255), 5)
            for result in resultsTracker:
                x1, y1, x2, y2, id = map(int, result)
                print(result)
                w, h = x2 - x1, y2 - y1
                cvzone.cornerRect(img, (x1, y1, w, h), l=9, rt=2, colorR=(255, 0, 255))
                cvzone.putTextRect(img, f' {int(id)}', (max(0, x1), max(35, y1)),
                scale=2, thickness=3, offset=10)

                cx, cy = x1 + w // 2, y1 + h // 2
                cv2.circle(img, (cx, cy), 5, (255, 0, 255), cv2.FILLED)

                # Count line check
                if (start_x < cx < end_x) and (start_y - 15 < cy < start_y + 15):
                    if id not in self.totalCount:
                        self.totalCount.append(id)
                        cv2.line(img, (start_x, start_y), (end_x, end_y), (0, 255, 0), 5)

            # cvzone.putTextRect(img, f' Count: {len(totalCount)}', (50, 50))
            cv2.putText(img,str(len(self.totalCount)),(255,100),cv2.FONT_HERSHEY_PLAIN,5,(50,50,255),8)


            img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            h, w, ch = img.shape
            bytes_per_line = ch * w
            qimg = QImage(img.data, w, h, bytes_per_line, QImage.Format_RGB888)
            self.update_frame.emit(qimg)

    def pause(self):
        self.paused = True

    def resume(self):
        self.paused = False

    def stop(self):
        if self.running:
            self.running = False
            self.quit()
            self.wait()
            if self.cap:
                self.cap.release()
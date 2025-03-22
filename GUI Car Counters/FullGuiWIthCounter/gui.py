from PySide6.QtWidgets import QMainWindow, QPushButton, QFileDialog, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QIcon
import cv2
from video_prcessing import VideoThread

class MainWindow(QMainWindow):
    # Global var for the main window
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon("assets/car_icon.ico"))
        self.setWindowTitle("Vehicle Counting System")
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

        self.select_mask_button = QPushButton("Select Mask")
        self.select_mask_button.setEnabled(False) 
        self.select_mask_button.clicked.connect(self.select_mask)
        button_layout.addWidget(self.select_mask_button)

        self.play_pause_button = QPushButton("Play")
        self.play_pause_button.setEnabled(False)
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
        self.mask_path = None
        self.is_playing = False

    def select_file(self):
        # Select the video file and sets the image
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Videos (*.mp4 *.mov *.avi)")
        if file_path:
            if self.is_playing:
                self.stop_video()
            self.video_path = file_path
            self.set_thumbnail(file_path)
    
    def get_image_size(self, image_path):
        """Returns width and height of an image using OpenCV."""
        img = cv2.imread(image_path)
        if img is None:
            return None
        return img.shape[1], img.shape[0]  # (width, height)

    def get_video_size(self, video_path):
        """Returns width and height of a video frame using OpenCV."""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        return width, height

    def select_mask(self):
        """Handles mask selection and validation."""
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Mask Image", "", "PNG Images (*.png)")
        if not file_path:
            return  # User canceled the file selection

        mask_size = self.get_image_size(file_path)

        # Ensure mask was loaded successfully
        if mask_size is None:
            QMessageBox.critical(self, "Error", "Failed to load mask image. Please select a valid PNG file.")
            return

        # Ensure a video is already selected before proceeding
        if not self.video_path:
            QMessageBox.warning(self, "Warning", "Please select a video first before adding a mask.")
            return

        # Get video size
        video_size = self.get_video_size(self.video_path)
        if video_size is None:
            QMessageBox.critical(self, "Error", "Failed to read video properties.")
            return

        # Compare mask and video sizes
        if mask_size != video_size:
            QMessageBox.critical(self, "Size Mismatch", "The mask size does not match the video size!")
            return

        # Now safe to assign the mask path
        self.mask_path = file_path
        self.video_thread.set_mask_source(self.mask_path)

        # Enable the play button since both video and mask are valid
        self.play_pause_button.setEnabled(True)
        QMessageBox.information(self, "Mask Loaded", "Mask successfully loaded!")




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
            self.select_mask_button.setEnabled(True)
        else:
            self.video_label.setText("Failed to load thumbnail")


    # def toggle_play_pause(self):
    #     if self.is_playing:
    #         self.stop_video()
    #         self.play_pause_button.setText("Play")
    #     else:
    #         self.play_pause_button.setText("Pause")
    #         self.start_video()

    def toggle_play_pause(self):
        if self.is_playing:
            self.video_thread.pause()
            self.is_playing = False
            self.play_pause_button.setText("Play")
        else:
            if self.video_thread.paused:  # Resume instead of restarting
                self.video_thread.resume()
            else:
                self.start_video()
            self.is_playing = True
            self.play_pause_button.setText("Pause")


    def start_video(self):
        if self.video_path:
            self.video_thread.set_video_source(self.video_path)
            self.video_thread.start()
            self.is_playing = True
        else:
            self.video_label.setText("Please select a video first.")
            # self.is_playing = False
            self.play_pause_button.setText("Play")

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
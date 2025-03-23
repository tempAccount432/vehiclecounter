from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSpinBox, QFileDialog, QMessageBox, QBoxLayout, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QIcon
import cv2
from video_prcessing import VideoThread

class MainWindow(QMainWindow):
    # Global var for the main window
    def __init__(self):
        super().__init__()

        # Video Thread
        self.video_thread = VideoThread()
        self.video_thread.update_frame.connect(self.display_frame)
        self.video_path = None
        self.mask_path = None
        self.is_playing = False
        self.initUI()

    def initUI(self): 
        self.setWindowIcon(QIcon("assets/car_icon.ico"))
        self.setWindowTitle("Vehicle Counting System")
        # self.setGeometry(100, 100, 684, 437)
        self.setGeometry(100, 100, 900, 600)
        self.setMinimumSize(684, 437)

        # Main central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main Layout (Horizontal)
        main_layout = QHBoxLayout(central_widget)
        # Remove margins/spaces
        # main_layout.setContentsMargins(0, 0, 0, 0)
        # main_layout.setSpacing(0)

        # Left Panel (Buttons & Inputs)
        left_panel_widget = QWidget()  # Wrap layout in QWidget
        left_panel = QVBoxLayout(left_panel_widget) 
        # **Key**: Remove margins & spacing, align top
        # left_panel.setContentsMargins(0, 0, 0, 0)
        # left_panel.setSpacing(0)
        left_panel.setAlignment(Qt.AlignTop)

        # Select File Button
        self.select_file_btn = QPushButton("Select File")
        self.select_file_btn.clicked.connect(self.select_file)
        left_panel.addWidget(self.select_file_btn)

        # Select Mask Button
        self.select_mask_btn = QPushButton("Select Mask")
        self.select_mask_btn.clicked.connect(self.select_mask)
        self.select_mask_btn.setEnabled(False)
        left_panel.addWidget(self.select_mask_btn)

        # Count Line Section
        # count_line_label = QLabel("Count Line")
        # left_panel.addWidget(count_line_label)

        count_line_group = QGroupBox("Count Line")   # Title
        count_line_layout = QVBoxLayout(count_line_group)
        count_line_layout.setContentsMargins(5, 5, 5, 5)  # Inside group margin
        count_line_layout.setSpacing(5)

        self.startx_spinbox = self.create_spinbox("Start_x:", 0, 1920, 400)
        count_line_layout.addLayout(self.startx_spinbox[1])

        self.starty_spinbox = self.create_spinbox("Start_y:", 0, 1080, 297)
        count_line_layout.addLayout(self.starty_spinbox[1])

        self.endx_spinbox = self.create_spinbox("End_x:", 0, 1920, 673)
        count_line_layout.addLayout(self.endx_spinbox[1])

        self.endy_spinbox = self.create_spinbox("End_y:", 0, 1080, 297)
        count_line_layout.addLayout(self.endy_spinbox[1])

        left_panel.addWidget(count_line_group)

        # Play Button
        self.play_pause_btn = QPushButton("Play")
        self.play_pause_btn.setEnabled(False)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        left_panel.addWidget(self.play_pause_btn)

        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.close)
        left_panel.addWidget(self.quit_button)

        # Right Panel (Video Display)
        self.video_label = QLabel("No Video Selected")
        self.video_label.setAlignment(Qt.AlignCenter)

        # Add to layout
        main_layout.addWidget(left_panel_widget)
        main_layout.addWidget(self.video_label)

        # Enforce 1:2 ratio with stretch factors
        main_layout.setStretchFactor(left_panel_widget, 1)  
        main_layout.setStretchFactor(self.video_label, 4)

        # Optionally, set a minimum width to the right panel
        # so it doesn't shrink too small
        self.video_label.setMinimumWidth(400)

        central_widget.setLayout(main_layout)


    def create_spinbox(self, label_text, min_val, max_val, default_val):
        layout = QHBoxLayout()
        label = QLabel(label_text)
        spinbox = QSpinBox()
        spinbox.setRange(min_val, max_val)
        spinbox.setValue(default_val)
        layout.addWidget(label)
        layout.addWidget(spinbox)
        return spinbox, layout

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
        self.play_pause_btn.setEnabled(True)
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
            self.select_mask_btn.setEnabled(True)
        else:
            self.video_label.setText("Failed to load thumbnail")

    def toggle_play_pause(self):
        if self.is_playing:
            self.video_thread.pause()
            self.is_playing = False
            self.play_pause_btn.setText("Play")
             # Update the count line limits
            self.video_thread.limits = [
                self.startx_spinbox[0].value(),
                self.starty_spinbox[0].value(),
                self.endx_spinbox[0].value(),
                self.endy_spinbox[0].value()
            ]
        else:
            if self.video_thread.paused:  # Resume instead of restarting
                self.video_thread.resume()
            else:
                self.start_video()
            self.is_playing = True
            self.play_pause_btn.setText("Pause")

    def start_video(self):
        if self.video_path:
            self.video_thread.set_video_source(self.video_path)
            self.video_thread.start()
            self.is_playing = True
        else:
            self.video_label.setText("Please select a video first.")
            # self.is_playing = False
            self.play_pause_btn.setText("Play")

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
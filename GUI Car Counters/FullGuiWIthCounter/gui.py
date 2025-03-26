from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSpinBox, QFileDialog, QMessageBox, QGroupBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage, QIcon
import cv2
from video_processing import VideoThread

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
        self.file_path_changed = False
        self.initUI()

    def initUI(self): 
        self.setWindowIcon(QIcon("assets/car_icon.ico"))
        self.setWindowTitle("Vehicle Counting System")
        # self.setGeometry(100, 100, 684, 437)
        self.setGeometry(100, 100, 900, 600)
        self.setMinimumSize(684, 437)
        # self.setFixedSize(684, 437)

        # Main central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main Layout (Horizontal)
        main_layout = QHBoxLayout(central_widget)

        # Left Panel (Buttons & Inputs)
        left_panel_widget = QWidget()
        left_panel = QVBoxLayout(left_panel_widget) 
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
        self.file_path_changed = False
        if self.is_playing:
            self.stop_video()

        file_path, _ = QFileDialog.getOpenFileName(self, "Select Video File", "", "Videos (*.mp4 *.mov *.avi)")
        if file_path:
           self.video_path = file_path
           self.file_path_changed = True

           self.video_thread.stop() 
           self.video_thread.totalCount = []
           self.video_thread.set_video_source(self.video_path)
           
           self.set_thumbnail(file_path)
           self.select_mask_btn.setEnabled(True)
           self.play_pause_btn.setEnabled(False)

           # If we already have a mask_path, check if it still matches the new video
        if self.mask_path:
            if self.is_mask_valid_for_video(self.mask_path, self.video_path):
                # If the old mask is still valid, re-enable Play
                self.play_pause_btn.setEnabled(True)
            else:
                # Old mask is invalid for new video
                self.play_pause_btn.setEnabled(False)
                QMessageBox.information(
                    self, "Mask Invalid",
                    "The previously selected mask does not match the new video's size. Please select a new mask."
                )
                self.mask_path = None
    
    def get_image_size(self, image_path):
        img = cv2.imread(image_path)
        if img is None:
            return None
        return img.shape[1], img.shape[0]  # (width, height)

    def get_video_size(self,video_path):
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return None
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        return (width, height)

    def select_mask(self):
        if self.is_playing:
            # Do not allow changing mask while playing
            QMessageBox.warning(self, "Warning", "Pause the video before selecting a new mask.")
            return
        
        file_path, _ = QFileDialog.getOpenFileName(self, "Select Mask Image", "", "PNG Images (*.png)")
        if not file_path:
            return 

        mask_size = self.get_image_size(file_path)
        if mask_size is None:
            QMessageBox.critical(self, "Error", "Failed to load mask image. Please select a valid PNG file.")
            return

        if not self.video_path:
            QMessageBox.warning(self, "Warning", "Please select a video first before adding a mask.")
            return

        if not self.is_mask_valid_for_video(file_path, self.video_path):
            return

        # video_size = self.get_video_size(self.video_path)
        # if video_size is None:
        #     QMessageBox.critical(self, "Error", "Failed to read video properties.")
        #     return

        # if mask_size != video_size:
        #     QMessageBox.critical(self, "Size Mismatch", "The mask size does not match the video size!")
            return

        self.mask_path = file_path
        self.video_thread.set_mask_source(self.mask_path)
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
            self.select_mask_btn.setEnabled(True) # Maybe I want to remove this line
        else:
            self.video_label.setText("Failed to load thumbnail")

# DON'T DELETE THIS FUNCTION
    # def toggle_play_pause(self): 
    #     if self.is_playing:
    #         self.video_thread.pause()
    #         self.is_playing = False
    #         self.play_pause_btn.setText("Play")
            
    #         # Re-enable select file & select mask
    #         self.select_file_btn.setEnabled(True)
    #         self.select_mask_btn.setEnabled(True)
    #     else:
    #         if self.video_thread.paused: 
    #             self.video_thread.resume()
    #         else:
    #             self.start_video()
    #             self.is_playing = True
    #         self.play_pause_btn.setText("Pause")
    #         self.select_file_btn.setEnabled(False)
    #         self.select_mask_btn.setEnabled(False)
    def toggle_play_pause(self): 
            if self.is_playing:
                self.video_thread.pause()
                self.is_playing = False
                self.play_pause_btn.setText("Play")
                self.select_file_btn.setEnabled(True)
                self.select_mask_btn.setEnabled(True)

            elif self.is_playing == False and self.file_path_changed == True:
                self.is_playing = True
                self.start_video_from_start()
                print("from 1st elif")
                self.play_pause_btn.setText("Pause")
                self.select_file_btn.setEnabled(False)
                self.select_mask_btn.setEnabled(False)
                self.file_path_changed = False
            elif self.is_playing ==False:
                # self.video_thread.resume()
                self.start_video()
                self.play_pause_btn.setText("Pause")
                self.select_file_btn.setEnabled(False)
                self.select_mask_btn.setEnabled(False)
                print("from  2nd elif")

                
                

    def start_video(self):
        if not self.video_path:
            self.video_label.setText("Please select a video first.")
            self.is_playing = False
            self.play_pause_btn.setText("Play")
            return

        # Update the count line limits
        self.video_thread.limits = [
            self.startx_spinbox[0].value(),
            self.starty_spinbox[0].value(),
            self.endx_spinbox[0].value(),
            self.endy_spinbox[0].value()
        ]

        # self.video_thread.stop()          
        # self.video_thread.totalCount = []  
        # self.video_thread.set_video_source(self.video_path)
        self.video_thread.resume()
        self.is_playing = True

    def start_video_from_start(self):
        if not self.video_path:
            self.video_label.setText("Please select a video first.")
            self.is_playing = False
            self.play_pause_btn.setText("Play")
            return

        # Update the count line limits
        self.video_thread.limits = [
            self.startx_spinbox[0].value(),
            self.starty_spinbox[0].value(),
            self.endx_spinbox[0].value(),
            self.endy_spinbox[0].value()
        ]

        self.video_thread.stop()          
        self.video_thread.totalCount = []  
        self.video_thread.set_video_source(self.video_path)
        self.video_thread.start()
        self.is_playing = True

    def stop_video(self):
        self.video_thread.stop()
        self.is_playing = False
        self.play_pause_btn.setText("Play")

        # Re-enable file & mask selection
        self.select_file_btn.setEnabled(True)
        self.select_mask_btn.setEnabled(True)

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

    def is_mask_valid_for_video(self, mask_path, video_path):
            """Check if existing/new mask matches the new video's size."""
            mask_size = self.get_image_size(mask_path)
            if mask_size is None:
                QMessageBox.critical(self, "Error", "Failed to load mask image.")
                return False

            video_size = self.get_video_size(video_path)
            if video_size is None:
                QMessageBox.critical(self, "Error", "Failed to read video properties.")
                return False

            if mask_size != video_size:
                QMessageBox.critical(self, "Size Mismatch", "The mask size does not match the video size!")
                return False

            return True

    def display_frame(self, qimg):
        pixmap = QPixmap.fromImage(qimg)
        self.video_label.setPixmap(pixmap)
        self.video_label.setScaledContents(True)
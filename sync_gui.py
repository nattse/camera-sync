#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 31 15:35:04 2023

@author: nathanieltse
"""
import cv2
import numpy as np
import matplotlib.pyplot as plt
import sys
import PyQt5
from PyQt5.QtGui import QPixmap, QColor, QImage
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDateTimeEdit,
    QDial,
    QDoubleSpinBox,
    QFontComboBox,
    QLabel,
    QLCDNumber,
    QLineEdit,
    QMainWindow,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSlider,
    QSpinBox,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QFileDialog,
    QListWidget,
    QAbstractItemView,
    QTabWidget
)

class FileBrowser(QWidget):

    def __init__(self):
        QWidget.__init__(self)
        layout = QHBoxLayout()
        layout_left = QVBoxLayout()
        layout_right = QVBoxLayout()
        browse_button = QPushButton('select videos')
        browse_button.clicked.connect(self.browse_files)
        layout_left.addWidget(browse_button)
        self.start_button = QPushButton('start video sync')
        self.start_button.setDisabled(True)
        self.start_button.clicked.connect(self.start)
        layout_left.addWidget(self.start_button)
        self.vid_list = QListWidget()
        self.vid_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout_right.addWidget(self.vid_list)
        remove_button = QPushButton('remove videos')
        remove_button.clicked.connect(self.remove_vids)
        layout_right.addWidget(remove_button)
        layout.addLayout(layout_left)
        layout.addLayout(layout_right)
        self.setLayout(layout)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle("File Browsing Dialog")
        self.setFixedSize(400, 300)
        self.show()
        
    def browse_files(self):
        videos = QFileDialog.getOpenFileNames(self, caption='Choose Video Files')[0]
        self.vid_list.addItems(videos)
        self.start_button.setDisabled(False)
        
    def remove_vids(self):
        #print([i.row() for i in self.vid_list.selectedIndexes()])             # Can't iterate over indexes b/c every item removed changes the index 
        for item in self.vid_list.selectedItems():                             # Instead, get the actual items that are selected
            for i in range(self.vid_list.count()):                             # and iterate through each item in the QListWidget
                if self.vid_list.item(i) == item:                              # and if that list item is the one we are looking for 
                    row_to_remove = self.vid_list.row(item)                    # get its place in the QListWidget
                    self.vid_list.takeItem(row_to_remove)                      # and remove
                    
    def start(self):
        self.hide()
        self.window = sync_window(self.vid_list)
        self.window.show()

class sync_window(QMainWindow):
    
    def __init__(self, vid_list):
        super().__init__()
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle('process')
        #layout = QHBoxLayout()
        self.tabs = QTabWidget()
        for i in range(vid_list.count()):
            vid_name = vid_list.item(i).text()
            try:
                short_name = vid_name.split('/')[-1]
            except:
                try:
                    short_name = vid_name.split('\\')[-1]
                except:
                    short_name = vid_name
            self.tabs.addTab(presync(vid_name), short_name)
        self.setCentralWidget(self.tabs)
    
class presync(QWidget):
    
    def __init__(self, vid_name):
        super().__init__()
        self.run_sync(vid_name)
        self.redo.clicked.connect(lambda: self.clearLayout(vid_name))
        try:
            self.short_name = vid_name.split('/')[-1]
        except:
            try:
                self.short_name = vid_name.split("\\")[-1]
            except:
                self.short_name = vid_name
        
    def convert_cv_qt(self, cv_img):
        """Convert from an opencv image to QPixmap"""
        rgb_image = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_image.shape
        bytes_per_line = ch * w
        convert_to_Qt_format = QImage(rgb_image.data, w, h, bytes_per_line, QImage.Format_RGB888)
        p = convert_to_Qt_format.scaled(w, h, Qt.KeepAspectRatio)
        return QPixmap.fromImage(p)
    
    def run_sync(self, vid_name):
        self.sync_window = sync(vid_name)
        images_to_check = self.sync_window.returns
        frame_num = self.sync_window.frame_num
        self.end_images = QVBoxLayout()
        self.commands = QVBoxLayout()
        self.total_tab = QHBoxLayout()
        if images_to_check is None or frame_num is None:
            self.show_error()
        else:
            conv = self.convert_cv_qt(images_to_check['signal off'])
            self.image_label_off = QLabel(self)
            self.textLabel_off = QLabel('off')
            self.end_images.addWidget(self.image_label_off)
            self.end_images.addWidget(self.textLabel_off)
            height, width = images_to_check['signal off'].shape[0], images_to_check['signal off'].shape[1]
            grey = QPixmap(width, height)
            self.image_label_off.setPixmap(conv)
            
            conv_on = self.convert_cv_qt(images_to_check['signal on'])
            self.image_label_on = QLabel(self)
            self.textLabel_on = QLabel(f'on {frame_num}')
            self.end_images.addWidget(self.image_label_on)
            self.end_images.addWidget(self.textLabel_on)
            height, width = images_to_check['signal on'].shape[0], images_to_check['signal on'].shape[1]
            grey = QPixmap(width, height)
            self.image_label_on.setPixmap(conv_on)
        
        self.begin_trim = QPushButton('trim video')
        self.begin_trim.clicked.connect(lambda: self.start_cutting(vid_name))
        self.commands.addWidget(self.begin_trim)
        self.redo = QPushButton('redo')
        self.commands.addWidget(self.redo)
        self.total_tab.addLayout(self.end_images)
        self.total_tab.addLayout(self.commands)
        self.setLayout(self.total_tab)
        self.show()
        
    def start_cutting(self, vid_name):
        prefix, suffix = vid_name.split('.')
        new_path = prefix + '-frame_synced.' + suffix
        print(new_path)
        cap = cv2.VideoCapture(vid_name)
        length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        code = cap.get(cv2.CAP_PROP_FOURCC)
        codec = int(code).to_bytes(4, byteorder=sys.byteorder).decode()
        self.output = cv2.VideoWriter(new_path, 
                                 cv2.VideoWriter_fourcc(*codec),
                                 30, (width,height))
        cap.set(cv2.CAP_PROP_POS_FRAMES,self.sync_window.frame_num)
        print(f'starting frames here: {self.sync_window.frame_num}')
        count = 0
        while True:
            count += 1
            print(f'counting frames: {count}')
            flag, frame = cap.read()
            pos_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
            if not flag:
                continue
            if pos_frame == length:
                break
            self.output.write(frame)
        cap.release()
        self.output.release()
    
    def clearLayout(self, vid_name):
        self.image_label_off.deleteLater()
        self.textLabel_off.deleteLater()
        self.image_label_on.deleteLater()
        self.textLabel_on.deleteLater()
        self.sync_window = sync(vid_name)
        images_to_check = self.sync_window.returns
        frame_num = self.sync_window.frame_num
        if images_to_check is None or frame_num is None:
            self.show_error()
        else:
            conv = self.convert_cv_qt(images_to_check['signal off'])
            self.image_label_off = QLabel(self)
            self.textLabel_off = QLabel('off')
            self.end_images.addWidget(self.image_label_off)
            self.end_images.addWidget(self.textLabel_off)
            height, width = images_to_check['signal off'].shape[0], images_to_check['signal off'].shape[1]
            grey = QPixmap(width, height)
            self.image_label_off.setPixmap(conv)
            
            conv_on = self.convert_cv_qt(images_to_check['signal on'])
            self.image_label_on = QLabel(self)
            self.textLabel_on = QLabel(f'on {frame_num}')
            self.end_images.addWidget(self.image_label_on)
            self.end_images.addWidget(self.textLabel_on)
            height, width = images_to_check['signal on'].shape[0], images_to_check['signal on'].shape[1]
            grey = QPixmap(width, height)
            self.image_label_on.setPixmap(conv_on)
            self.begin_trim.setDisabled(False)
        self.show()
        
    def show_error(self):
        self.image_label_off = QLabel(self)
        self.textLabel_off = QLabel('error')
        self.image_label_on = QLabel(self)
        self.textLabel_on = QLabel('error')
        return
    
class sync(QWidget):
    
    def __init__(self, vid_name):
        super().__init__()
        
        def frame_color(frame_data):
            z = frame_data.reshape((-1,3))
            z = np.float32(z)
            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            k = 2
            ret,label,center=cv2.kmeans(z,
                                       k,
                                       None,
                                       criteria,
                                       10,
                                       cv2.KMEANS_RANDOM_CENTERS)
            _, counts = np.unique(label, return_counts=True)
            dominant = center[np.argmax(counts)]
            return dominant

        def display_on_off_signal(start,end,r,cap):
            cap.set(cv2.CAP_PROP_POS_FRAMES,start)
            while True:
                flag, frame = cap.read()
                if flag:
                    sig_off_frame = frame[int(r[1]):int(r[1]+r[3]), int(r[0]):int(r[0]+r[2])]
                    break
            cap.set(cv2.CAP_PROP_POS_FRAMES,end)
            while True:
                flag, frame = cap.read()
                if flag:
                    sig_on_frame = frame[int(r[1]):int(r[1]+r[3]), int(r[0]):int(r[0]+r[2])]
                    break
            return(sig_off_frame, sig_on_frame)

        def onChange(trackbarValue):
            cap.set(cv2.CAP_PROP_POS_FRAMES,trackbarValue)
            flag,frame = cap.read()
            cv2.imshow("video", frame)
            pass
        
        cap = cv2.VideoCapture(vid_name)
        length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cv2.namedWindow('video')
        cv2.createTrackbar( 'sig_off', 'video', 0, length, onChange )
        cv2.createTrackbar( 'sig_on'  , 'video', 100, length, onChange )
        onChange(0)
        cv2.waitKey()
        start = cv2.getTrackbarPos('sig_off','video')
        end = cv2.getTrackbarPos('sig_on','video')
        framerange = (start,end)
        cv2.destroyAllWindows()
        cap.set(cv2.CAP_PROP_POS_FRAMES,start)
        while True:
            flag, frame = cap.read()
            if flag:
                pos_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
                cv2.imshow('video', frame)
                break
        r = cv2.selectROI(frame)
        cv2.destroyAllWindows()
        frame_colors = []
        for frame in range(*framerange):
            cap.set(cv2.CAP_PROP_POS_FRAMES,frame)
            while True:
                flag, frame = cap.read()
                if flag:
                    raw_array = frame[int(r[1]):int(r[1]+r[3]), int(r[0]):int(r[0]+r[2])]
                    break
            fc = frame_color(raw_array)
            frame_colors.append(fc/255)
        fc = np.array(frame_colors)
        criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
        try:
            ret,label,center=cv2.kmeans(fc,                                    # If you place the first slider later
                                       2,                                      # than the second slider, you'll get an
                                       None,                                   # data0.dims <= 2 && type == CV_32F && K > 0 in function 'kmeans'     
                                       criteria,                               # error, so return nothing and signal to redo  
                                       10,
                                       cv2.KMEANS_RANDOM_CENTERS)
        except cv2.error as error:
            self.returns = None
            self.frame_num = None
            return
        switch_frame = np.where(label!=label[1])[0][0] + framerange[0] 
        images_to_check = {}
        images_to_check['signal off'], images_to_check['signal on'] = display_on_off_signal(switch_frame - 1,
                                                                                            switch_frame,
                                                                                            r, 
                                                                                            cap)
        self.returns = images_to_check
        self.frame_num = switch_frame
        
        
f = FileBrowser()
#temp_path = '/Users/nathanieltse/Documents/anipose_test/inbox_3cam/today_cam/videos-raw/mouse_1_3_cam2_trimmedDLC_resnet101_inOFcamsApr5shuffle4_640000.mov'
#if __name__ == '__main__':
#    app = QApplication(sys.argv)
#    ex = FileBrowser()
#    sys.exit(app.exec_())

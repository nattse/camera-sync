#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Do not use this, for it uses cap.set(cv2.CAP_PROP_POS_FRAMES,self.sync_window.frame_num) which is not trustworthy.
I only keep it to remember how I originally structured the GUI.
"""
import cv2
import time
import numpy as np
import matplotlib.pyplot as plt
import sys
from tqdm import tqdm
import PyQt5
from PyQt5.QtGui import QPixmap, QColor, QImage
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QMainWindow,
    QPushButton,
    QSlider,
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
        #self.setWindowFlags(Qt.WindowStaysOnTopHint)
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

"""Creates and contains tabs"""
class sync_window(QMainWindow):
    def __init__(self, vid_list):
        super().__init__()
        #self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setWindowTitle('process')
        self.tabs = QTabWidget()
        self.tab_dict = {}
        for i in range(vid_list.count()):
            vid_name = vid_list.item(i).text()
            try:
                short_name = vid_name.split('/')[-1]
            except:
                try:
                    short_name = vid_name.split('\\')[-1]
                except:
                    short_name = vid_name
            self.tab_dict[vid_name] = presync(vid_name)
            self.tabs.addTab(self.tab_dict[vid_name], short_name)
        self.tabs.addTab(batch_cut(self.tab_dict), 'batch trim')
        self.setCentralWidget(self.tabs)

"""Creates a tab option to process all videos at once"""
class batch_cut(QWidget):
    def __init__(self, tab_dict):
        super().__init__()
        self.batch_run = QVBoxLayout()
        self.run = QPushButton('batch trim')
        self.run.clicked.connect(lambda: self.run_everyone(tab_dict))
        self.batch_run.addWidget(self.run)
        self.setLayout(self.batch_run)
        self.show()
    def run_everyone(self, tab_dict):
        for vid_name in tab_dict.keys():
            tab_dict[vid_name].start_cutting(vid_name)

"""Creates a tab layout for a single video, automatically runs the kmeans program via the sync class, displays
the results, and presents options to redo or cut the video"""
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
        dropped_count = 0
        frame_time = time.time()
        for a in tqdm(range(length - self.sync_window.frame_num)):
            count += 1
            flag, frame = cap.read()
            pos_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
            #print(f'total frames: {length}')
            #print(f'counting frames: {pos_frame}')
            if time.time() - frame_time > 5:
                if pos_frame > (length - 10):
                    print(f'looks like we got stuck at {pos_frame} out of {length}, breaking')
                    break
            if not flag:
                dropped_count += 1
                continue
            if pos_frame >= length:
                print('finished cutting!')
                break
            self.output.write(frame)
            frame_time = time.time()
        cap.release()
        self.output.release()
        print(f'Thought you should know\nDropped {dropped_count} out of {count} frames')
    
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
    
"""The kmeans frame finding process itself"""
class sync(QWidget):
    def __init__(self, vid_name, elaborate = False):
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

        def show_frame_of_interest(framenumber,r,cap):
            cap.set(cv2.CAP_PROP_POS_FRAMES,framenumber)
            while True:
                flag, frame = cap.read()
                if flag:
                    frame_of_interest = frame[int(r[1]):int(r[1]+r[3]), int(r[0]):int(r[0]+r[2])]
                    break
            z = frame_of_interest.reshape((-1,3))
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
            center = np.uint8(center)
            res = center[label.flatten()]
            res = np.flip(res, axis=1) # Since we are planning on showing in plt, need to flip
            res2 = res.reshape((frame_of_interest.shape)) 
            ordered_colors = [color for order,color in sorted(zip(counts, center), key = lambda pair: pair[0], reverse=True)]
            ordered_colors = [np.flip(i) for i in ordered_colors] # Also going to show in plt
            return label, np.flip(frame_of_interest, axis=2), res2, ordered_colors
            
        def show_work(framerange, r, cap):
            fig, axs = plt.subplots(4, len(range(*framerange)))
            fig.subplots_adjust(wspace=0, hspace=0)
            fig.tight_layout()
            dominant_color = []
            for count, i in enumerate(range(*framerange)):
                label, frame_of_interest, res2, colorlist = show_frame_of_interest(i, r, cap)
                axs[0, count].imshow(frame_of_interest)
                axs[1, count].imshow(res2)
                for ind, color in enumerate(colorlist):
                    color = color / 255
                    axs[2, count].bar(0, 1 / (3 ** ind), color = color)
                axs[2, count].set_aspect('equal')
                for i in [0, 1, 2, 3]:
                    axs[i, count].set_xticks([])
                    axs[i, count].set_yticks([])
                    axs[i, count].xaxis.set_tick_params(labelbottom=False)
                    axs[i, count].yaxis.set_tick_params(labelleft=False)
                dominant_color.append(colorlist[0])

            criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)
            ret,label,center=cv2.kmeans(np.float32(np.array(dominant_color)),
                                       2,
                                       None,
                                       criteria,
                                       10,
                                       cv2.KMEANS_RANDOM_CENTERS)
            switch_fr = np.where(label!=label[0])[0][0]
            for count, ax in enumerate(axs[3, :]):
                if count == switch_fr:
                    ax.set_facecolor('black')
                    axs[0, count].set_title(count + framerange[0])
            plt.show()
        
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
        cap.set(cv2.CAP_PROP_POS_FRAMES,end)
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
        switch_frame = np.where(label!=label[0])[0][0] + framerange[0] 
        images_to_check = {}
        images_to_check['signal off'], images_to_check['signal on'] = display_on_off_signal(switch_frame - 1,
                                                                                            switch_frame,
                                                                                            r, 
                                                                                            cap)
        self.returns = images_to_check
        self.frame_num = switch_frame

        if elaborate:
            show_work(framerange, r, cap)
        
       
if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = FileBrowser()
    sys.exit(app.exec_())

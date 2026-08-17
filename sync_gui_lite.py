#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon Jul 31 15:35:04 2023

@author: nathanieltse
"""
import cv2
import time
import subprocess
import numpy as np
import matplotlib.pyplot as plt
import sys
from tqdm import tqdm
import PyQt5
from PyQt5.QtGui import QPixmap, QColor, QImage
from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QLabel,
    QMainWindow,
    QPushButton,
    QRubberBand,
    QSlider,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QFileDialog,
    QListWidget,
    QAbstractItemView,
    QTabWidget,
    QMessageBox
)
import os
import pandas as pd

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
        self.quick_cut_button = QPushButton('quick cut video')
        self.quick_cut_button.setDisabled(True)
        self.quick_cut_button.clicked.connect(self.quick_cut)
        layout_left.addWidget(self.quick_cut_button)
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
        self.setFixedSize(400, 340)
        self.show()
        
    def browse_files(self):
        videos = QFileDialog.getOpenFileNames(self, caption='Choose Video Files')[0]
        self.vid_list.addItems(videos)
        self.start_button.setDisabled(False)
        self.quick_cut_button.setDisabled(False)
        
    def remove_vids(self):
        #print([i.row() for i in self.vid_list.selectedIndexes()])             # Can't iterate over indexes b/c every item removed changes the index 
        for item in self.vid_list.selectedItems():                             # Instead, get the actual items that are selected
            for i in range(self.vid_list.count()):                             # and iterate through each item in the QListWidget
                if self.vid_list.item(i) == item:                              # and if that list item is the one we are looking for 
                    row_to_remove = self.vid_list.row(item)                    # get its place in the QListWidget
                    self.vid_list.takeItem(row_to_remove)                      # and remove
                    
    def quick_cut(self):
        selected = self.vid_list.selectedItems()
        target = selected[0].text() if selected else self.vid_list.item(0).text()
        if not os.path.splitext(target)[1].lower() == '.avi':                   # Quick Cut stream-copies, which only cuts exactly on
            if not self.warn_not_avi(target):                                   # all-intra video, so bail out unless told otherwise
                return
        self.quick_cut_windows = getattr(self, 'quick_cut_windows', [])
        w = QuickCutWindow(target)
        self.quick_cut_windows.append(w)

    def warn_not_avi(self, target):
        """Warn that Quick Cut is only frame accurate on the mjpeg .avi files convert.sh makes.
        Returns True if the user wants to go ahead anyway."""
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Warning)
        box.setWindowTitle('Not an .avi - frame numbers will be wrong')
        box.setText(f'{os.path.basename(target)} is not an .avi file.')
        box.setInformativeText(
            'Quick Cut copies streams instead of re-encoding, so it can only cut exactly on '
            'all-intra video - the mjpeg .avi files convert.sh produces.\n\n'
            'On an inter-frame video like a GoPro .MP4, ffmpeg cannot cut mid-GOP. It drops the '
            'frames between your cut point and the next keyframe and leaves a gap at the start of '
            'the "_after" file. Converting that file to .avi afterwards pads the gap with duplicate '
            'frames, which shifts every frame number you read off the cut video - by a different '
            'amount for each camera.\n\n'
            'Convert to .avi first with convert.sh, then Quick Cut the .avi.'
        )
        box.setStandardButtons(QMessageBox.Cancel | QMessageBox.Ignore)
        box.setDefaultButton(QMessageBox.Cancel)
        return box.exec_() == QMessageBox.Ignore

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

        self.export_button = QPushButton('Export data')
        self.export_button.clicked.connect(lambda: self.export(tab_dict))
        self.batch_run.addWidget(self.export_button)

        self.setLayout(self.batch_run)
        self.show()
    def run_everyone(self, tab_dict):
        for vid_name in tab_dict.keys():
            tab_dict[vid_name].start_cutting(vid_name)
    def export(self, tab_dict):
        for vid_name in tab_dict.keys():
            tab_dict[vid_name].export_data(vid_name)

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
        images_to_check = self.sync_window.returns # Dictionary containing the selected area of video frame during last signal off and first signal on 
        self.masterFrameNum = self.sync_window.frame_num # The actual frame number where off turns to on

        self.end_images = QVBoxLayout()
        self.commands = QVBoxLayout()
        self.total_tab = QHBoxLayout()
        if images_to_check is None or self.masterFrameNum is None:
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
            self.textLabel_on = QLabel(f'on {self.masterFrameNum}')
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

        self.increments = QHBoxLayout()
        self.frameBack = QPushButton('Frame back')
        self.frameBack.clicked.connect(self.setFrameBack)
        self.increments.addWidget(self.frameBack)
        self.frameNext = QPushButton('Frame forward')
        self.frameNext.clicked.connect(self.setFrameNext)
        self.increments.addWidget(self.frameNext)
        self.commands.addLayout(self.increments)

        self.total_tab.addLayout(self.end_images)
        self.total_tab.addLayout(self.commands)
        self.setLayout(self.total_tab)
        self.show()

    def setFrameBack(self):
        self.masterFrameNum -= 1
        frameROI = self.sync_window.get_frame_image(self.masterFrameNum - 1)
        frameROI = self.convert_cv_qt(frameROI)
        self.image_label_off.setPixmap(frameROI)

        frameROI_on = self.sync_window.get_frame_image(self.masterFrameNum)
        frameROI_on = self.convert_cv_qt(frameROI_on)
        self.image_label_on.setPixmap(frameROI_on)


    def setFrameNext(self):
        self.masterFrameNum += 1
        frameROI = self.sync_window.get_frame_image(self.masterFrameNum - 1)
        frameROI = self.convert_cv_qt(frameROI)
        self.image_label_off.setPixmap(frameROI)

        frameROI_on = self.sync_window.get_frame_image(self.masterFrameNum)
        frameROI_on = self.convert_cv_qt(frameROI_on)
        self.image_label_on.setPixmap(frameROI_on)
        
    def start_cutting(self, vid_name):
        base, ext = os.path.splitext(vid_name)
        new_path = base + '-frame_synced' + ext
        print(new_path)
        cap = cv2.VideoCapture(vid_name)
        length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        if ext.lower() == '.mp4':
            codec = 'mp4v'
        else:
            code = cap.get(cv2.CAP_PROP_FOURCC)
            codec = int(code).to_bytes(4, byteorder=sys.byteorder).decode()
        print(f'\n\n\nWARNING: cutting with sync_gui_lite limits your output video to 30 FPS - use' \
              f'sync_decapitator if you need a different FPS or want to do the processing somewhere' \
              f'other than this computer\n\n\n')
        self.output = cv2.VideoWriter(new_path, 
                                 cv2.VideoWriter_fourcc(*codec),
                                 30, (width,height))
        cap.set(cv2.CAP_PROP_POS_FRAMES, self.masterFrameNum)
        print(f'starting frames here: {self.masterFrameNum}')
        count = 0
        dropped_count = 0
        frame_time = time.time()
        for a in tqdm(range(length)):
            count += 1
            flag, frame = cap.read()
            pos_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
            if pos_frame < self.masterFrameNum:
                continue
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
    def export_data(self, vid_name):
        batch_dir = os.path.split(vid_name)[0]
        data_file = 'cut_times.csv'
        batch_data_file = os.path.join(batch_dir, data_file)
        if os.path.isfile(batch_data_file):
            df = pd.read_csv(batch_data_file, index_col = 0)
        else:
            df = pd.DataFrame()
        print(f'Exporting {vid_name} to csv...')
        df.loc[os.path.split(vid_name)[-1], 'frame'] = self.masterFrameNum
        df.to_csv(batch_data_file)

    def clearLayout(self, vid_name):
        self.image_label_off.deleteLater()
        self.textLabel_off.deleteLater()
        self.image_label_on.deleteLater()
        self.textLabel_on.deleteLater()
        self.sync_window = sync(vid_name)
        images_to_check = self.sync_window.returns
        self.masterFrameNum = self.sync_window.frame_num
        if images_to_check is None or self.masterFrameNum is None:
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
            self.textLabel_on = QLabel(f'on {self.masterFrameNum}')
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
    
class FrameRangeSelector(QDialog):
    """Modal dialog for selecting sig_off / sig_on frame range with Qt sliders."""
    def __init__(self, cap, length, parent=None):
        super().__init__(parent)
        self._cap = cap
        self.setWindowTitle('Select frame range')
        layout = QVBoxLayout()

        self._frame_label = QLabel()
        self._frame_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._frame_label)

        self._info_label = QLabel()
        self._info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self._info_label)

        layout.addWidget(QLabel('Signal Off (start of range):'))
        self.off_slider = QSlider(Qt.Horizontal)
        self.off_slider.setRange(0, length)
        self.off_slider.setValue(0)
        self.off_slider.setFocusPolicy(Qt.StrongFocus)
        self.off_slider.valueChanged.connect(lambda v: self._show_frame(v, 'off'))
        layout.addWidget(self.off_slider)

        layout.addWidget(QLabel('Signal On (end of range):'))
        self.on_slider = QSlider(Qt.Horizontal)
        self.on_slider.setRange(0, length)
        self.on_slider.setValue(min(100, length))
        self.on_slider.setFocusPolicy(Qt.StrongFocus)
        self.on_slider.valueChanged.connect(lambda v: self._show_frame(v, 'on'))
        layout.addWidget(self.on_slider)

        hint = QLabel('Tab between sliders  |  ← → arrows move frame by frame')
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)

        ok_btn = QPushButton('Confirm range')
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)

        self.setLayout(layout)
        self._show_frame(0, 'off')

    def _show_frame(self, frame_num, source):
        self._cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        flag, frame = self._cap.read()
        if flag:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            qt_img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
            self._frame_label.setPixmap(
                QPixmap.fromImage(qt_img).scaled(800, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )
        name = 'Signal Off' if source == 'off' else 'Signal On'
        self._info_label.setText(
            f'{name}: frame {frame_num}   |   Off: {self.off_slider.value()}   On: {self.on_slider.value()}'
        )

    def get_range(self):
        return self.off_slider.value(), self.on_slider.value()


class ROIDrawWidget(QLabel):
    """QLabel subclass that lets the user rubber-band a rectangle."""
    def __init__(self, cv_frame):
        super().__init__()
        self._orig_h, self._orig_w = cv_frame.shape[:2]
        rgb = cv2.cvtColor(cv_frame, cv2.COLOR_BGR2RGB)
        qt_img = QImage(rgb.data, self._orig_w, self._orig_h, self._orig_w * 3, QImage.Format_RGB888)
        self._pixmap = QPixmap.fromImage(qt_img).scaled(800, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.setPixmap(self._pixmap)
        self.setFixedSize(self._pixmap.size())
        self._disp_w = self._pixmap.width()
        self._disp_h = self._pixmap.height()
        self._start = None
        self._end = None
        self._rubber = QRubberBand(QRubberBand.Rectangle, self)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._start = event.pos()
            self._rubber.setGeometry(QRect(self._start, QSize()))
            self._rubber.show()

    def mouseMoveEvent(self, event):
        if self._start:
            self._rubber.setGeometry(QRect(self._start, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self._start:
            self._end = event.pos()
            self._rubber.setGeometry(QRect(self._start, self._end).normalized())

    def get_roi(self):
        if self._start is None or self._end is None:
            return (0, 0, self._orig_w, self._orig_h)
        rect = QRect(self._start, self._end).normalized()
        sx = self._orig_w / self._disp_w
        sy = self._orig_h / self._disp_h
        return (int(rect.x() * sx), int(rect.y() * sy),
                int(rect.width() * sx), int(rect.height() * sy))


class ROISelector(QDialog):
    """Modal dialog that shows a frame and lets the user drag an ROI rectangle."""
    def __init__(self, cv_frame, parent=None):
        super().__init__(parent)
        self.setWindowTitle('Select ROI — click and drag, then confirm')
        layout = QVBoxLayout()
        self._draw = ROIDrawWidget(cv_frame)
        layout.addWidget(self._draw)
        hint = QLabel('Click and drag to select the region of interest')
        hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(hint)
        ok_btn = QPushButton('Confirm ROI')
        ok_btn.clicked.connect(self.accept)
        layout.addWidget(ok_btn)
        self.setLayout(layout)

    def get_roi(self):
        return self._draw.get_roi()


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
        self.vidName = vid_name
        cap = cv2.VideoCapture(vid_name)
        length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        range_dlg = FrameRangeSelector(cap, length)
        if range_dlg.exec_() != QDialog.Accepted:
            self.returns = None
            self.frame_num = None
            cap.release()
            return
        start, end = range_dlg.get_range()
        framerange = (start, end)

        cap.set(cv2.CAP_PROP_POS_FRAMES, end)
        while True:
            flag, frame = cap.read()
            if flag:
                break

        roi_dlg = ROISelector(frame)
        if roi_dlg.exec_() != QDialog.Accepted:
            self.returns = None
            self.frame_num = None
            cap.release()
            return
        r = roi_dlg.get_roi()
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
        self.r = r

        if elaborate:
            show_work(framerange, r, cap)

    def get_frame_image(self, frameNum):
        cap = cv2.VideoCapture(self.vidName)
        length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.set(cv2.CAP_PROP_POS_FRAMES, frameNum)
        while True:
            flag, frame = cap.read()
            if flag:
                frameROI = frame[int(self.r[1]):int(self.r[1] + self.r[3]), int(self.r[0]):int(self.r[0] + self.r[2])]
                break
        return frameROI
       
class QuickCutWindow(QWidget):
    def __init__(self, vid_path):
        super().__init__()
        self.vid_path = vid_path
        self.cap = cv2.VideoCapture(vid_path)
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.fps = self.cap.get(cv2.CAP_PROP_FPS)
        self.current_frame = 0

        self.is_avi = os.path.splitext(vid_path)[1].lower() == '.avi'
        self.setWindowTitle(f'Quick Cut - {os.path.basename(vid_path)}')
        main_layout = QVBoxLayout()

        if not self.is_avi:                                                     # Keep the warning on screen, not just in a dialog you
            self.warning_banner = QLabel(                                       # clicked through five minutes ago
                'WARNING: this is not an .avi - cutting it will shift every frame number '
                'in the "_after" file. Convert with convert.sh first.'
            )
            self.warning_banner.setAlignment(Qt.AlignCenter)
            self.warning_banner.setWordWrap(True)
            self.warning_banner.setStyleSheet(
                'background-color: #ffcc00; color: black; padding: 6px; font-weight: bold;'
            )
            main_layout.addWidget(self.warning_banner)

        self.frame_label = QLabel()
        self.frame_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.frame_label)

        self.frame_info = QLabel()
        self.frame_info.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.frame_info)

        self.slider = QSlider(Qt.Horizontal)
        self.slider.setRange(0, max(0, self.total_frames - 1))
        self.slider.sliderMoved.connect(self._update_label_only)
        self.slider.sliderReleased.connect(lambda: self.display_frame(self.slider.value()))
        main_layout.addWidget(self.slider)

        nav = QHBoxLayout()
        prev_btn = QPushButton('< Frame')
        prev_btn.clicked.connect(self.prev_frame)
        next_btn = QPushButton('Frame >')
        next_btn.clicked.connect(self.next_frame)
        nav.addWidget(prev_btn)
        nav.addWidget(next_btn)
        main_layout.addLayout(nav)

        self.cut_btn = QPushButton('Cut here' if self.is_avi else 'Cut here (not frame accurate!)')
        self.cut_btn.clicked.connect(self.cut_video)
        main_layout.addWidget(self.cut_btn)

        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.status_label)

        self.setLayout(main_layout)
        self.display_frame(0)
        self.show()

    def _fmt_info(self, frame_num):
        t = frame_num / self.fps if self.fps > 0 else 0
        return f'Frame: {frame_num} / {max(0, self.total_frames - 1)}   Time: {t:.3f}s'

    def _update_label_only(self, value):
        self.frame_info.setText(self._fmt_info(value))

    def convert_cv_qt(self, cv_img):
        rgb = cv2.cvtColor(cv_img, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        qt_img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
        return QPixmap.fromImage(qt_img).scaled(800, 500, Qt.KeepAspectRatio, Qt.SmoothTransformation)

    def display_frame(self, frame_num):
        self.current_frame = frame_num
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_num)
        flag, frame = self.cap.read()
        if flag:
            self.frame_label.setPixmap(self.convert_cv_qt(frame))
        self.frame_info.setText(self._fmt_info(frame_num))

    def prev_frame(self):
        new = max(0, self.current_frame - 1)
        self.slider.setValue(new)
        self.display_frame(new)

    def next_frame(self):
        new = min(self.total_frames - 1, self.current_frame + 1)
        self.slider.setValue(new)
        self.display_frame(new)

    def cut_video(self):
        cut_time = self.current_frame / self.fps if self.fps > 0 else 0
        base, ext = os.path.splitext(self.vid_path)
        before_path = base + '_before' + ext
        after_path = base + '_after' + ext

        self.status_label.setText('Cutting...')
        self.cut_btn.setDisabled(True)
        QApplication.processEvents()

        try:
            subprocess.run(
                ['ffmpeg', '-i', self.vid_path, '-to', f'{cut_time:.6f}', '-c', 'copy', '-y', before_path],
                check=True, capture_output=True
            )
            subprocess.run(
                ['ffmpeg', '-i', self.vid_path, '-ss', f'{cut_time:.6f}', '-c', 'copy', '-y', after_path],
                check=True, capture_output=True
            )
            self.status_label.setText(
                f'Done! {os.path.basename(before_path)}  +  {os.path.basename(after_path)}'
            )
        except FileNotFoundError:
            self.status_label.setText('Error: ffmpeg not found — please install ffmpeg.')
        except subprocess.CalledProcessError as e:
            self.status_label.setText('Error: ffmpeg failed — see terminal for details.')
            print(e.stderr.decode())
        finally:
            self.cut_btn.setDisabled(False)

    def closeEvent(self, event):
        self.cap.release()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = FileBrowser()
    sys.exit(app.exec_())

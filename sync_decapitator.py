import os
import cv2
import pandas as pd
import sys
from tqdm import tqdm
import time

"""From the command line, simply run `python sync_decapitator.py CUTFILE INDEX FPS`
CUTFILE is the cut_times.csv file you got from sync_gui_lite.py - make sure this file and the video files are in the same directory!
INDEX is the file you'd like to cut, 1-indexed. Use -1 to cut all files in the .csv
FPS is the original videos frames per second
"""

class cutter:
    def __init__(self, batch_data_file, index = -1, vid_FPS = 30):
        folder = os.path.split(batch_data_file)[0]
        vid_list = pd.read_csv(batch_data_file, index_col = 0)
        vid_files = os.listdir(os.path.split(batch_data_file)[0])
        vid_files = [i for i in vid_files if not i.startswith('.')]
        vid_files = [i for i in vid_files if not 'frame_synced' in i]
        if not index == -1:
            to_read = vid_list.columns[index]
            to_read_vid = [i for i in vid_files if i == to_read]
            assert len(to_read_vid) == 1
            self.start_cutting(to_read_vid[0])
        else:
            for to_read, frame in vid_list.iterrows():
                print(f'Video file: {to_read}, frame: {frame}')
                to_read_vid = [i for i in vid_files if i == to_read]
                assert len(to_read_vid) == 1
                video_path = os.path.join(folder, to_read_vid[0])
                self.start_cutting(video_path, frame['frame'], vid_FPS)

    def start_cutting(self, vid_name, split_frame, vid_FPS):
            prefix, suffix = vid_name.split('.')
            new_path = prefix + '-frame_synced.' + suffix
            print(f'Cutting up {vid_name} into')
            print(new_path)
            cap = cv2.VideoCapture(vid_name)
            length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            code = cap.get(cv2.CAP_PROP_FOURCC)
            codec = int(code).to_bytes(4, byteorder=sys.byteorder).decode()
            self.output = cv2.VideoWriter(new_path, 
                                     cv2.VideoWriter_fourcc(*codec),
                                     vid_FPS, (width,height))
            count = 0
            dropped_count = 0
            frame_time = time.time()
            for a in tqdm(range(length)):
                count += 1
                flag, frame = cap.read()
                pos_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
                if pos_frame < split_frame:
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


if __name__ == '__main__':
    path_input = sys.argv[1]
    index_input = int(sys.argv[2])
    fps_input = int(sys.argv[3])
    cutter(path_input, index_input, fps_input) # The cut_times.csv file location, the index of the file you want to cut, and the FPS

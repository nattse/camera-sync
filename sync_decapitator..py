import os
import cv2
import pandas as pd
import sys
from tqdm import tqdm
import time

class cutter:
    def __init__(self, batch_data_file, index = None):
        folder = os.path.split(batch_data_file)[0]
        vid_list = pd.read_csv(batch_data_file, index_col = 0)
        vid_files = os.listdir(os.path.split(batch_data_file)[0])
        vid_files = [i for i in vid_files if not i.startswith('.')]
        vid_files = [i for i in vid_files if not 'frame_synced' in i]
        if not index is None:
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
                self.start_cutting(video_path, frame['frame'])

    def start_cutting(self, vid_name, split_frame):
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
                                     30, (width,height))
            #cap.set(cv2.CAP_PROP_POS_FRAMES,self.sync_window.frame_num)
            print(f'starting frames here: {split_frame}')
            count = 0
            dropped_count = 0
            frame_time = time.time()
            for a in tqdm(range(length)):
                count += 1
                flag, frame = cap.read()
                pos_frame = cap.get(cv2.CAP_PROP_POS_FRAMES)
                if pos_frame < split_frame:
                    continue
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


if __name__ == '__main__':
    if len(sys.argv) >= 2:
        cutter(sys.argv[1])
    else:
        cutter(sys.argv[1], sys.argv[2])

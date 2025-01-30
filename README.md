# Camera-Sync

Trim video to the exact frame without loss of quality.

A simple way to synchronize any number of videos using a visual cue, created for use in 3D tracking via [DeepLabCut](https://github.com/DeepLabCut/DeepLabCut) or [Anipose](https://github.com/lambdaloop/anipose). 

*Audio is not currently included*

## Installation

1. Download this repository or use `git clone https://github.com/nattse/camera-sync`

2. Navigate to downloaded repository and using [Anaconda](https://www.anaconda.com/download), install required packages using `conda env create -n camera-sync --file environment.yml`

3. Activate environment using `conda activate camera-sync`

4. Start GUI with `python3 sync_gui_lite.py`

### Alternative

This program is still quite small and you may already have `opencv`, `matplotlib` and `pyqt` (and their dependencies) installed. In that case, you can simply save **sync_gui.py** and start with `python3 sync_gui.py`

## Process overview

1. Select the video files to be synced and proceed to *start video sync*

<p align="center">
<img src="https://github.com/nattse/camera_sync/blob/main/store/browse.png" width="400">
</p>

2. Use both sliders to find where the synchronizing signal turns on in the video. Place the top slider right before the signal turns ON and the bottom slider right after the signal is ON.
   
<p align="center">
<img src="https://github.com/nattse/camera_sync/blob/main/store/pre_sig_1.png" width="400"> <img src="https://github.com/nattse/camera_sync/blob/main/store/post_sig_1.png" width="400">
</p>

<p align="center">
<img src="https://github.com/nattse/camera_sync/blob/main/store/pre_sig_2.png" width="400"> <img src="https://github.com/nattse/camera_sync/blob/main/store/post_sig_2.png" width="400">
</p>

<p align="center">
Top slider position: LED off (left). Bottom slider position: LED on (right)
</p>

3. To confirm choices, press ESC

4. Drag to draw rectangular ROI around signal. ROI only needs to be large enough that you can comfortably verify the signal on/off state in the next step. Press ESC

<p align="center">
<img src="https://github.com/nattse/camera_sync/blob/main/store/ROI_1.png" width="400">   <img src="https://github.com/nattse/camera_sync/blob/main/store/ROI_2.png" width="400">
</p>

5. Repeat signal OFF/ON, ROI selection process for each video

6. Inspect the results for each video. Top frame should show the cropped signal in the OFF state. Bottom frame should show the cropped signal in the ON state. If this is not the case, click *redo*, otherwise proceed to *trim video* on the spot, or export all of the syncing video frames in one file, cut_times.csv. The latter is recommended, as **sync_gui_lite.py automatically assumes your videos are recorded at 30 FPS**, whereas sync_decapitator.py allows you to specify the framerate.
   
<p align="center">
<img src="https://github.com/nattse/camera_sync/blob/main/store/conf_1.png" width="300">  <img src="https://github.com/nattse/camera_sync/blob/main/store/conf_2.png" width="300">
</p>

7. If you choose to export the cut_times.csv file, ensure that csv file and all of the videos it references are contained in the same directory. From there, simply run `python sync_decapitator.py PATH_TO_CSV INDEX FRAMERATE`, where PATH_TO_CSV is what it sounds like, INDEX is the index of the video in cut_times.csv that you want to cut, and FRAMERATE is the FPS of your original video. In all cases, trimmed videos will be saved in the same folder as original videos, with the suffix “frame_synced” appended.

## Understanding the process

By drawing our ROI and positioning the sliders to straddle the frame where the signal changes, when we extract the frames that exist between the sliders, we (hopefully) end up with two groups of images that are very similar within the groups and very different between the groups. 

<p align="center">
<img src="https://github.com/nattse/camera-sync/blob/main/store/process_1.png" width="700"> 
</p>
<p align="center">
Extracted images
</p>

We can even further increase within-group similarity and between-group difference by using color quantization to choose to only look at the most prominent color

<p align="center">
<img src="https://github.com/nattse/camera-sync/blob/main/store/process_2.png" width="700"> 
</p>
<p align="center">
Images reduced to two colors
</p>
<p align="center">
<img src="https://github.com/nattse/camera-sync/blob/main/store/process_3.png" width="700"> 
</p>
<p align="center">
Image color composition with most prominent color on top
</p>

Finding the signal OFF and ON frames is then easily achieved using k-means clustering, and so we can align all videos to begin on the first signal ON frame.

<p align="center">
<img src="https://github.com/nattse/camera-sync/blob/main/store/process_4.png" width="700"> 
</p>
<p align="center">
First signal ON frame
</p>

Some pitfalls to watch out for:
- Objects passing between the camera and the signal during one of the extracted frames
- Slow or incomplete signal change

Increasing the slider width (extracting more frames) and drawing a larger ROI (diluting the signal pixels) will increase the chances of the signal info being affected by noise or background changes.

<p align="center">
<img src="https://github.com/nattse/camera-sync/blob/main/store/crop_perf_1.png" width="700"> 
</p>
<p align="center">
<img src="https://github.com/nattse/camera-sync/blob/main/store/crop_perf_2.png" width="700"> 
</p>
<p align="center">
<img src="https://github.com/nattse/camera-sync/blob/main/store/crop_perf_3.png" width="700"> 
</p>
<p align="center">
As the LED occupies less of the ROI, the variability in the dominant color may change significantly 
</p>



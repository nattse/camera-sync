# Camera-Sync
A simple way to synchronize any number of videos using a visual cue, created for use in 3D tracking via [DeepLabCut](https://github.com/DeepLabCut/DeepLabCut) or [Anipose](https://github.com/lambdaloop/anipose). 

*Audio is not currently included*

## Installation

1. Download this repository or use `git clone https://github.com/nattse/camera-sync`

2. Navigate to downloaded repository and using [Anaconda](https://www.anaconda.com/download), install required packages using `conda env create -n camera-sync --file environment.yml`

3. Activate environment using `conda activate camera-sync`

4. Start GUI with `python3 sync_gui.py`

### Alternative

This program is still quite small and you may already have `opencv`, `matplotlib` and `pyqt` (and their dependencies) installed. In that case, you can simply save **sync_gui.py** and start with `python3 sync_gui.py`
   
## Process overview

1. Select the video files to be synced and proceed to *start video sync*

<img src="https://github.com/nattse/camera_sync/blob/main/store/browse.png" width="400">


2. Adjust top slider bar to just before signal ON (does not need to be exact but getting it closer reduces the chances of having to redo this step)

<img src="https://github.com/nattse/camera_sync/blob/main/store/pre_sig_1.png" width="500">   <img src="https://github.com/nattse/camera_sync/blob/main/store/pre_sig_2.png" width="500">


3. Adjust bottom slider bar to frame when signal is ON (again, does not need to be exact but closer to the first frame of signal ON is better). To confirm choices, press ESC

<img src="https://github.com/nattse/camera_sync/blob/main/store/post_sig_1.png" width="500">   <img src="https://github.com/nattse/camera_sync/blob/main/store/post_sig_2.png" width="500">


4. Drag to draw rectangular ROI around signal. ROI only needs to be large enough that you can comfortably verify the signal on/off state in the next step. Press ESC

<img src="https://github.com/nattse/camera_sync/blob/main/store/ROI_1.png" width="400">   <img src="https://github.com/nattse/camera_sync/blob/main/store/ROI_2.png" width="400">


5. Repeat signal OFF/ON, ROI selection process for each video
Inspect the results for each video. Top frame should show the signal in the OFF state. Bottom frame should show the signal in the ON state. If this is not the case, click *redo*, otherwise proceed to *trim video*

<img src="https://github.com/nattse/camera_sync/blob/main/store/conf_1.png" width="300">  <img src="https://github.com/nattse/camera_sync/blob/main/store/conf_2.png" width="300">

Trimmed videos will be saved in the same folder as original videos, with the suffix “frame_synced” appended.

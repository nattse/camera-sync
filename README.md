# camera-sync
A simple way to synchronize any number of videos using a visual cue, created for use in 3D tracking via [DeepLabCut](https://github.com/DeepLabCut/DeepLabCut) or [Anipose](https://github.com/lambdaloop/anipose). 

*Audio is not currently included*

## Procedure

1. Save **sync_gui.py**
2. In terminal run:

`cd /where/you/saved/sync_gui.py`

`python3 sync_gui.py`

3. Select the video files to be synced and proceed to *start video sync*

![File select menu]( https://github.com/nattse/camera_sync/blob/main/store/browse.png)

4. Adjust top slider bar to just before signal ON (does not need to be exact but getting it closer reduces the chances of having to redo this step)

![Top slider, signal off, example 1](https://github.com/nattse/camera_sync/blob/main/store/pre_sig_1.png)

![Top slider, signal off, example 2](https://github.com/nattse/camera_sync/blob/main/store/pre_sig_2.png)

5. Adjust bottom slider bar to frame when signal is ON (again, does not need to be exact but closer to the first frame of signal ON is better). To confirm choices, press ESC

![Bottom slider, signal on, example 1](https://github.com/nattse/camera_sync/blob/main/store/post_sig_1.png)

![Bottom slider, signal on, example 2](https://github.com/nattse/camera_sync/blob/main/store/post_sig_2.png)

6. Drag to draw rectangular ROI around signal. ROI only needs to be large enough that you can comfortably verify the signal on/off state in the next step. Press ESC

![ROI bounding example 1](https://github.com/nattse/camera_sync/blob/main/store/ROI_1.png)

![ROI bounding example 2](https://github.com/nattse/camera_sync/blob/main/store/ROI_2.png)

7. Repeat signal OFF/ON, ROI selection process for each video
Inspect the results for each video. Top frame should show the signal in the OFF state. Bottom frame should show the signal in the ON state. If this is not the case, click *redo*, otherwise proceed to *trim video*

![Confirmation frames example 1](https://github.com/nattse/camera_sync/blob/main/store/conf_1.png)

![Confirmation frames example 2](https://github.com/nattse/camera_sync/blob/main/store/conf_2.png)

Trimmed videos will be saved in the same folder as original videos, with the suffix “frame_synced” appended.

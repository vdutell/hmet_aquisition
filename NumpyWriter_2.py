import numpy as np
import os
from video_capture.realsense2_backend import Realsense2_Source

class NumpyWriter():

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.frame_num = 0
        os.makedirs(base_dir)
        self.ts_filename = os.path.join(base_dir, "timestamps.csv")

    def write_video_frame(self, depth_frame):
        """
        This gets called when a new frame is read in.
        """
        # frame has .depth for raw numpy data
        # .timestamp
        with open(self.ts_filename, 'a+') as ts_file:
            ts_file.write(str(depth_frame.timestamp) + "\n")

        filename = os.path.join(self.base_dir, f"depth_frame_{self.frame_num}.npy")
        np.save(filename, np.array(depth_frame.depth))

        self.frame_num += 1

    def close(self):
        """
        This gets called when everthing is done.
        """
        pass


def start_depth_recording(self, rec_loc, start_time_synced):
    if not self.record_depth:
        return

    if self.depth_video_writer is not None:
        logger.warning("Depth video recording has been started already")
        return

    video_path = os.path.join(rec_loc, "depth")
    self.depth_video_writer = NumpyWriter(video_path)

Realsense2_Source.start_depth_recording = start_depth_recording

Realsense2_Source.DEFAULT_DEPTH_FPS = 90
Realsense2_Source.DEFAULT_COLOR_FPS = 90


# class d435i_odometry_writer():
#
#     def __init__(self, base_dir):
#         self.base_dir = base_dir
#         self.frame_num = 0
#         os.makedirs(base_dir)
#         self.ts_filename = os.path.join(base_dir, "timestamps.csv")
#
#     def write_video_frame(self, odo_data):
#         """
#         This gets called when a new frame is read in.
#         """
#         # frame has .depth for raw numpy data
#         # .timestamp
#         with open(self.ts_filename, 'a+') as ts_file:
#             ts_file.write(str(depth_frame.timestamp) + "\n")
#
#         filename = os.path.join(self.base_dir, f"depth_frame_{self.frame_num}.npy")
#         np.save(filename, np.array(depth_frame.depth))
#
#         self.frame_num += 1
#
#     def close(self):
#         """
#         This gets called when everthing is done.
#         """
#         pass
#
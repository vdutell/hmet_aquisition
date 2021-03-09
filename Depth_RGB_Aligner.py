import numpy as np
import os
import pyrealsense2 as rs

from video_capture.realsense2_backend import Realsense2_Source
from video_capture.realsense2_backend import ColorFrame
from video_capture.realsense2_backend import DepthFrame
#pipeline = Realsense2_Source.pipeline

TIMEOUT = 500

# Create an align object
#https://github.com/IntelRealSense/librealsense/blob/master/wrappers/python/examples/align-depth2color.py
# rs.align allows us to perform alignment of depth frames to others frames
# The "align_to" is the stream type to which we plan to align depth frames.
# In our case, we want to align our depth stream to RGB space.
align_to = rs.stream.color
align = rs.align(align_to)

#hijack the get_frames method to do alignment on the fly
def get_frames(self):
    if self.online:
        try:
            frames = self.pipeline.wait_for_frames(TIMEOUT)
            ### USE ALIGN METHOD TO ALIGN FRAMES ###
            aligned_frames = align.process(frames)

        except RuntimeError as e:
            logger.error("get_frames: Timeout!")
            raise RuntimeError(e)
        else:
            current_time = self.g_pool.get_timestamp()

            color = None
            # if we're expecting color frames
            if rs.stream.color in self.stream_profiles:
                ### USE ALIGNED FRAME INSTEAD OF FRAME ###
                color_frame = aligned_frames.get_color_frame()
                last_color_frame_ts = color_frame.get_timestamp()
                if self.last_color_frame_ts != last_color_frame_ts:
                    self.last_color_frame_ts = last_color_frame_ts
                    color = ColorFrame(
                        np.asanyarray(color_frame.get_data()),
                        current_time,
                        self.color_frame_index,
                    )
                    self.color_frame_index += 1

            depth = None
            # if we're expecting depth frames
            if rs.stream.depth in self.stream_profiles:
                ### USE ALIGNED FRAME INSTEAD OF FRAME ###
                depth_frame = aligned_frames.get_depth_frame()
                last_depth_frame_ts = depth_frame.get_timestamp()
                if self.last_depth_frame_ts != last_depth_frame_ts:
                    self.last_depth_frame_ts = last_depth_frame_ts
                    depth = DepthFrame(
                        np.asarray(depth_frame.get_data(),dtype=np.uint16),
                        current_time,
                        self.depth_frame_index,
                    )
                    self.depth_frame_index += 1

            return color, depth
    return None, None

#replace the default frame capturer with our own
Realsense2_Source.get_frames = get_frames

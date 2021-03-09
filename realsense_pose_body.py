"""
(*)~---------------------------------------------------------------------------
Pupil - eye tracking platform
Copyright (C) 2012-2019 Pupil Labs
Distributed under the terms of the GNU
Lesser General Public License (LGPL v3.0).
See COPYING and COPYING.LESSER for license details.
---------------------------------------------------------------------------~(*)

Adapted from VEBD/pupil_plugins

"""
import multiprocessing as mp

import numpy as np

import pyrealsense2 as rs

import logging
from plugin import Plugin
from pyglui import ui
from uvc import get_time_monotonic
from file_methods import PLData_Writer

import traceback

logger = logging.getLogger(__name__)


class RealSense_Stream_Body(Plugin):
    """ Pupil Capture plugin for the Intel RealSense T265 tracking camera.
    This plugin, when activated, will start a connected RealSense T265 tracking
    camera and fetch odometry data (position, orientation, velocities) from it.
    When recording, the odometry will be saved to `odometry.pldata`.
    Note that the recorded timestamps come from uvc.get_time_monotonic and will
    probably have varying latency wrt the actual timestamp of the odometry
    data. Because of this, the timestamp from the T265 device is also recorded
    to the field `rs_timestamp`.
    """

    uniqueness = "unique"
    icon_font = "roboto"
    icon_chr = "B"


    def __init__(self, g_pool):
        """ Constructor. """
        super().__init__(g_pool)
        logger.info(str(g_pool.process))
        self.proxy = None
        self.writer = None
        self.max_latency_ms = 1.
        self.verbose = False

        # initialize empty menu
        self.menu = None
        self.infos = {
            'sampling_rate': None,
            'confidence': None,
            'position': None,
            'orientation': None,
            'angular_velocity': None,
            'linear_velocity': None,
        }

        self.frame_queue = mp.Queue()
        self.pipeline = None
        self.started = False

        self._t_last = 0.

    @classmethod
    def start_pipeline(cls, callback=None):
        """ Start the RealSense pipeline. """
        pipeline = rs.pipeline()
        logger.info("LOADED PIPELINE")
        config = rs.config()
        #config.enable_device('0000909212111129')
        logger.info("CONFIG")
        config.enable_stream(rs.stream.pose)
        logger.info("STREAM")
        #sn = rs.camera_info.serial_number #THIS DOESNT WORK
        #logger.info(sn)

        if callback is None:
            pipeline.start(config)
        else:
            pipeline.start(config, callback)

        return pipeline

    def frame_callback(self, rs_frame):
        """ Callback for new RealSense frames. """
        if rs_frame.is_pose_frame() and self.frame_queue is not None:
            odometry = self.get_odometry(rs_frame, self._t_last)
            # TODO writing to the class attribute might be the reason for the
            #  jittery pupil timestamp. Maybe do the sample rate calculation
            #  in the main thread, assuming frames aren't dropped.
            self._t_last = odometry[0]
            self.frame_queue.put(odometry)

    @classmethod
    def get_odometry(cls, rs_frame, t_last):
        """ Get odometry data from RealSense pose frame. """
        t = rs_frame.get_timestamp() / 1e3
        t_pupil = get_time_monotonic()
        f = 1. / (t - t_last)

        pose = rs_frame.as_pose_frame()
        c = pose.pose_data.tracker_confidence
        p = pose.pose_data.translation
        q = pose.pose_data.rotation
        v = pose.pose_data.velocity
        w = pose.pose_data.angular_velocity

        return t, t_pupil, f, c, \
            (p.x, p.y, p.z), (q.w, q.x, q.y, q.z), \
            (v.x, v.y, v.z), (w.x, w.y, w.z)

    @classmethod
    def odometry_to_list_of_dicts(cls, odometry_data):
        """ Convert list of tuples to list of dicts. """
        return [
            {'topic': 'odometry_body', 'timestamp': t_pupil, 'rs_timestamp': t,
             'tracker_confidence': c, 'position': p, 'orientation': q,
             'linear_velocity': v, 'angular_velocity': w}
            for t, t_pupil, f, c, p, q, v, w in odometry_data]

    @classmethod
    def get_info_str(cls, values, axes, unit=None):
        """ Get string with current values for display. """
        if unit is None:
            return ', '.join(
                f'{a}: {v:.2f}' for v, a in zip(values, axes))
        else:
            return ', '.join(
                f'{a}: {v:.2f} {unit}' for v, a in zip(values, axes))

    def show_infos(self, t, t_pupil, f, c, p, q, v, w):
        """ Show current RealSense data in the plugin menu. """
        f = np.mean(f)
        c = np.mean(c)
        p = tuple(map(np.mean, zip(*p)))
        q = tuple(map(np.mean, zip(*q)))
        v = tuple(map(np.mean, zip(*v)))
        w = tuple(map(np.mean, zip(*w)))

        if self.infos['linear_velocity'] is not None:
            self.infos['sampling_rate'].text = f'Sampling rate: {f:.2f} Hz'
            self.infos['confidence'].text = f'Confidence: {c}'
            self.infos['position'].text = self.get_info_str(
                p, ('x', 'y', 'z'), 'm')
            self.infos['orientation'].text = self.get_info_str(
                q, ('w', 'x', 'y', 'z'))
            self.infos['linear_velocity'].text = self.get_info_str(
                v, ('x', 'y', 'z'), 'm/s')
            self.infos['angular_velocity'].text = self.get_info_str(
                w, ('x', 'y', 'z'), 'rad/s')

    def recent_events(self, events):
        """ Main loop callback. """
        if not self.started:
            return

        try:
            t = 0.
            t0 = self.g_pool.get_timestamp()
            #t0 = get_time_monotonic()
            odometry_data = []
            # Only get new frames from the queue for self.max_latency_ms
            while (t - t0) < self.max_latency_ms / 1000. \
                    and not self.frame_queue.empty():
                odometry_data.append(self.frame_queue.get())
                #t = get_time_monotonic()
                t = self.g_pool.get_timestamp()
            else:
                if self.verbose:
                    logger.info(
                        f'Stopped after fetching {len(odometry_data)} '
                        f'odometry frames. Will resume after next world '
                        f'frame.')

        except RuntimeError as e:
            logger.error(str(e))
            return

        # Show (and possibly record) collected odometry data
        if len(odometry_data) > 0:
            self.show_infos(*zip(*odometry_data))
            if self.writer is not None:
                for d in self.odometry_to_list_of_dicts(odometry_data):
                    try:
                        self.writer.append(d)
                    except AttributeError:
                        pass

    def cleanup(self):
        """ Cleanup callback. """
        if self.pipeline is not None:
            self.pipeline.stop()
            self.pipeline = None
            self.started = False

    def on_notify(self, notification):
        """ Callback for notifications. """
        # Start or stop recording base on notification
        if notification['subject'] == 'recording.started':
            if self.writer is None:
                self.writer = PLData_Writer(
                    notification['rec_path'], 'odometry_body')
        if notification['subject'] == 'recording.stopped':
            if self.writer is not None:
                self.writer.close()
                self.writer = None

    def add_info_menu(self, measure):
        """ Add growing menu with infos. """
        self.infos[measure] = ui.Info_Text('Waiting...')
        info_menu = ui.Growing_Menu(measure.replace('_', ' ').capitalize())
        info_menu.append(self.infos[measure])
        self.menu.append(info_menu)

    def init_ui(self):
        """ Initialize plugin UI. """
        self.add_menu()
        self.menu.label = "RealSense Stream Body"

        self.infos['sampling_rate'] = ui.Info_Text('Waiting...')
        self.menu.append(self.infos['sampling_rate'])
        self.infos['confidence'] = ui.Info_Text('')
        self.menu.append(self.infos['confidence'])

        self.add_info_menu('position')
        self.add_info_menu('orientation')
        self.add_info_menu('linear_velocity')
        self.add_info_menu('angular_velocity')

        try:
            # TODO dispatch to thread to avoid blocking
            self.pipeline = self.start_pipeline(self.frame_callback)
            self.started = True
        except Exception as e:
            logger.error(traceback.format_exc())

    def deinit_ui(self):
        """ De-initialize plugin UI. """
        self.remove_menu()
        self.cleanup()

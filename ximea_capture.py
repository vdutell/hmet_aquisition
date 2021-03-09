"""
(*)~---------------------------------------------------------------------------
Pupil - eye tracking platform
Copyright (C) 2012-2019 Pupil Labs

Distributed under the terms of the GNU
Lesser General Public License (LGPL v3.0).
See COPYING and COPYING.LESSER for license details.
---------------------------------------------------------------------------~(*)
"""

from plugin import Plugin
from pyglui.cygl.utils import draw_points_norm, RGBA, draw_gl_texture
from pyglui import ui
import gl_utils
import numpy as np

from video_overlay.plugins.generic_overlay import Video_Overlay

import threading
import ximea_utils

#logging
import logging
logger = logging.getLogger(__name__)

import os
import cv2


class Ximea_Capture(Plugin):
    """
    Ximea Capture captures frames from a Ximea camera
    during collection in parallel with world camera
    """
    #icon_chr = chr(0xEC09)
    #icon_font = "pupil_icons"
    icon_font = "roboto"
    icon_chr = "X"

    def __init__(self, g_pool,
    record_ximea=True, preview_ximea=False,
    serial_num='XECAS1922001', subject='TEST_SUBJECT', task='TEST_TASK',
     yaml_loc='/home/vasha/cy.yaml', imshape=(1544, 2064), ims_per_file=400):
        super().__init__(g_pool)
        self.order = 0.1
        #self.pupil_display_list = []

        self.record_ximea = record_ximea
        self.preview_ximea = preview_ximea
        self.serial_num = serial_num
        self.yaml_loc = yaml_loc
        self.subject = subject
        self.task = task
        self.imshape = imshape
        self.ims_per_file = ims_per_file

        self.camera = None
        self.image_handle = None
        self.camera_open = False
        self.save_queue =  None
        self.blink_counter = 0

        #self.save_folder = g_pool.rec_dir

        self.stop_collecting_event = threading.Event()
        self.currently_recording =  threading.Event()
        self.currently_saving =  threading.Event()

        try:
            self.camera, self.image_handle, self.camera_open = ximea_utils.init_camera(self.serial_num, self.yaml_loc, logger)
        except Exception as e:
            logger.info(f'Problem with Opening Camera: {e}')
            self.preview_ximea = False
            self.record_ximea = False
        #time sync protocol
        # def get_timestamp():
        #     return get_time_monotonic() - g_pool.timebase.value
        # g_pool.get_timestamp = get_timestamp
        # g_pool.get_now = get_time_monotonic

    def init_ui(self):
        self.add_menu()
        self.menu.label = "Ximea Cpature"

        def set_record(record_ximea):
            self.record_ximea = record_ximea
            # try:
            #     self.camera, self.image_handle, self.camera_open = ximea_utils.init_camera(self.serial_num, self.yaml_loc, logger)
            # except Exception as e:
            #     logger.info('Unable to Open Camera for Recording!')
            #     logger.info(f'Error: {e}')
            #     self.preview_ximea = False
            #     self.record_ximea = False
        def set_preview(preview_ximea):
            self.preview_ximea = preview_ximea
            if(self.currently_recording.is_set() & self.preview_ximea):
                logger.info('Cant preview while recording')
            # try:
            #     self.camera, self.image_handle, self.camera_open = ximea_utils.init_camera(self.serial_num, self.yaml_loc, logger)
            # except Exception as e:
            #     logger.info('Unable to Open Camera for Recording!')
            #     logger.info(f'Error: {e}')
            #     self.preview_ximea = False
            #     self.record_ximea = False
        def set_serial_num(new_serial_num):
            self.serial_num = new_serial_num
            if not self.camera == None:
                self.camera.close_device()
            try:
                self.camera, self.image_handle, self.camera_open = ximea_utils.init_camera(self.serial_num, self.yaml_loc, logger)
            except Exception as e:
                logger.info(f'Problem with Serial Number: {e}')
                self.preview_ximea = False
                self.record_ximea = False
        def set_subject_id(new_subject):
            self.subject = new_subject
        def set_task_name(new_task_name):
            self.task = new_task_name
        def set_yaml_loc(new_yaml_loc):
            self.yaml_loc = new_yaml_loc
            if not self.camera == None:
                self.camera.close_device()
            try:
                self.camera, self.image_handle, self.camera_open = ximea_utils.init_camera(self.serial_num, self.yaml_loc, logger)
            except Exception as e:
                logger.info(r'Problem with Yaml File: {e}')
                self.preview_ximea = False
                self.record_ximea = False
        help_str = "Ximea Capture Captures frames from Ximea Cameras in Parallel with Record."
        self.menu.append(ui.Info_Text(help_str))
        self.menu.append(ui.Text_Input("serial_num", self, setter=set_serial_num, label="Serial Number"))
        self.menu.append(ui.Switch("preview_ximea",self, setter=set_preview, label="Preview Ximea Cameras"))
        self.menu.append(ui.Text_Input("yaml_loc", self, setter=set_yaml_loc, label="Cam Settings Location"))
        self.menu.append(ui.Text_Input("subject", self, setter=set_subject_id, label="Subject ID"))
        self.menu.append(ui.Text_Input("task", self, setter=set_task_name, label="Task Name"))
        self.menu.append(ui.Switch("record_ximea",self, setter=set_record, label="Record From Ximea Cameras"))

        # set_save_dir()

    def gl_display(self):
        # blink?
        if int(self.blink_counter / 10) % 2 == 1:
            if self.currently_recording.is_set():
                draw_points_norm([(0.01,0.1)], size=35, color=RGBA(0.1, 1.0, 0.1, 0.8))
            if self.currently_saving.is_set():
                draw_points_norm([(0.01,0.01)], size=35, color=RGBA(1.0, 0.1, 0.1, 0.8))
        self.blink_counter += 1

        if(self.preview_ximea):
            if(self.currently_recording.is_set()):
                #if we are currently saving, don't grab images
                im = np.ones((*self.imshape,3)).astype(np.uint8)
                alp=0
            elif(not self.camera_open):
                logger.info(f'Unable to Open Camera!')
                self.preview_ximea = False
                im = np.zeros((*self.imshape,3)).astype(np.uint8)
                alp = 0.5
            else:
                im = ximea_utils.decode_ximea_frame(self.camera, self.image_handle, self.imshape, logger)
                alp=1
            #cv2.imshow('image',im)
            #cv2.imwrite('/home/vasha/img.png', im)
            gl_utils.make_coord_system_norm_based()
            draw_gl_texture(im, interpolation=True, alpha=alp)

        if(self.record_ximea):
            if not self.camera_open:
                logger.info('Camera Not Open!')
                self.record_ximea = False

    def get_init_dict(self):
        return {}

    def on_notify(self, notification):
        '''
        when we are notified that recording has started - begin our own Recording
        '''
        if notification.get("subject") == 'recording.started':
            self.save_dir = os.path.join(notification.get("rec_path"),'ximea')

            if(self.record_ximea):
                logger.info('Starting Recording from Ximea Cameras...')
                logger.info(f'Saving Ximea Frames at {self.save_dir}...')
                self.stop_collecting_event.clear()
                os.mkdir(self.save_dir)
                self.save_queue = ximea_utils.start_ximea_aquisition(self.camera, self.image_handle,
                                                   self.save_dir, self.ims_per_file,
                                                   self.stop_collecting_event,
                                                   self.currently_recording,
                                                   self.currently_saving,
                                                   self.g_pool,
                                                   logger)
                ximea_utils.write_user_info(self.save_dir, self.subject, self.task)

            else:
                logger.info('Recording WITHOUT Ximea Cameras')

        elif notification.get("subject") == 'recording.stopped':
            if(self.record_ximea):
                logger.info('Stopping Recording from Ximea Cameras...')
                self.stop_collecting_event.set()
            else:
                logger.info('Did NOT Record from Ximea Cameras')

    def on_char(self,char):
        '''
        When we hit record, also start recording from ximea cameras
        '''
        # if(char=='r'):
        #     if(self.record_ximea):
        #         if(self.currently_recording.is_set()):
        #             logger.info('Stopping Recording from Ximea Cameras...')
        #             self.stop_collecting_event.set()
        #
        #         else:
        #             logger.info('Starting Recording from Ximea Cameras...')
        #             logger.info(f'Saving Ximea Frames at {self.save_dir}...')
        #             self.stop_collecting_event.clear()
        #             self.save_queue = ximea_utils.start_ximea_aquisition(self.camera, self.image_handle,
        #                                                self.save_dir, self.ims_per_file,
        #                                                self.stop_collecting_event,
        #                                                self.currently_recording,
        #                                                self.currently_saving,
        #                                                self.g_pool,
        #                                                logger)

        return(False)

    def deinit_ui(self):
        self.remove_menu()

    def cleanup(self):
        """
        gets called when the plugin get terminated.
        This happens either voluntarily or forced.
        if you have an gui or glfw window destroy it here.
        """
        if not self.camera == None:
            self.camera.close_device()

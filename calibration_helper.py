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

from video_overlay.plugins.generic_overlay import Video_Overlay

#logging
import logging
logger = logging.getLogger(__name__)

class Calibration_Helper(Plugin):
    """
    Calibration Helper displays calibration guides in the world camera to aid in calibration
    during collection in parallel with world camera
    """
    #icon_chr = chr(0xEC09)
    #icon_font = "pupil_icons"
    icon_font = "roboto"
    icon_chr = "C"

    def __init__(self, g_pool, calibration_crosses=False):
        super().__init__(g_pool)
        self.order = 0.8

        self.calibration_crosses = calibration_crosses


    def init_ui(self):
        self.add_menu()
        self.menu.label = "Calibration Helper"

        def set_record(record_ximea):
            self.record_ximea = record_ximea
        def set_calib(calibration_crosses):
            self.calibration_crosses = calibration_crosses

        help_str = "Calibration Overlay displays guides in the world camera to aid in calibration."
        self.menu.append(ui.Info_Text(help_str))
        self.menu.append(ui.Switch("calibration_crosses",self, setter=set_calib, label="View Calibration Helpers"))

    def gl_display(self):

        if(self.calibration_crosses):
            low_v = 0.2
            mid_v = 0.5
            high_v = 0.8
            low_h = 0.2
            mid_h = 0.5
            high_h = 0.8
            s = 150
            c = RGBA(1.0, 1.0, 1.0, 0.5)
            draw_points_norm([(low_h,low_v)], size=s, color=c)
            draw_points_norm([(low_h,mid_v)], size=s, color=c)
            draw_points_norm([(low_h,high_v)], size=s, color=c)
            draw_points_norm([(high_h,low_v)], size=s, color=c)
            draw_points_norm([(high_h,mid_v)], size=s, color=c)
            draw_points_norm([(high_h,high_v)], size=s, color=c)
            draw_points_norm([(mid_h,low_v)], size=s, color=c)
            draw_points_norm([(mid_h,mid_v)], size=s, color=c)
            draw_points_norm([(mid_h,high_v)], size=s, color=c)

    def get_init_dict(self):
        return {}

    def on_char(self,char):
        '''
        Turn on and off with x
        '''
        if(char=='x'):
            if(self.calibration_crosses):
                self.calibration_crosses = False
            else:
                self.calibration_crosses = True
        return(False)

    def deinit_ui(self):
        self.remove_menu()


    def cleanup(self):
        """
        gets called when the plugin get terminated.
        This happens either voluntarily or forced.
        if you have an gui or glfw window destroy it here.
        """
        pass

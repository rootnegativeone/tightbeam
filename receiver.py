import transceiver
import sys

# test 2 (pass) --------------------------------------------------------------------------------------------
# output string(s) from glyph sequence
#video = '/user/Downloads/VID_20171021_145821.mp4'
#frame_list = transceiver.capture_frames_from_video(video)
#transceiver.decode_frames_into_strings(frame_list)

# test 3 (fail) --------------------------------------------------------------------------------------------
# decompose 5 MB JPEG, display glyph sequence, render same image on display
# extra small (401 B; 4 x 10^2): /user/.ssh/id_rsa.pub
#video = '/user/Downloads/VID_20171022_153304.mp4'
#frame_list = transceiver.capture_frames_from_video(video)
#transceiver.decode_frames_into_strings(frame_list)

# TODO: refactor so receiver.py can receive and process looping video from transmitter.py
transceiver.capture_frames_from_device()


# small (5 kB; 5 x 10^3):
# medium (50 kB; 5 x 10^4):
# large (400.3 kB; 4 x 10^5): /user/PycharmProjects/transceiver/Images/license.jpg
# extra large (5 MB; 5 x 10^6): TODO: find 5 MB image































'''
Kivy app:

# -*- coding: utf-8 -*-
import kivy
kivy.require('1.9.1') # replace with your current kivy version!

from kivy.app import App
from kivy.uix.label import Label


class MyApp(App):

    def build(self):
        return Label(text='Coffee?')


if __name__ == '__main__':
    MyApp().run()

'''




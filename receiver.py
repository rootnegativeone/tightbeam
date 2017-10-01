# test 2 (fail)
# output string(s) from glyph sequence

import transceiver
import sys

# test 2:
video = '/user/Downloads/test2.mp4'
frame_list = transceiver.capture_frames_from_video(video)
transceiver.decode_frames_into_strings(frame_list)


















# test 3 (fail)
# decompose 5 MB JPEG, display glyph sequence, render same image on display

# test 3:
# small (401 B): /user/.ssh/id_rsa.pub
# medium (400.3 kB): /user/PycharmProjects/transceiver/Images/license.jpg
# large (5 MB): TODO: find 5 MB image































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




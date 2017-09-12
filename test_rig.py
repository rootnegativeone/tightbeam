# test 1 (pass)
# display glyph sequence that contains init, payload (public key), and end strings

# test 2 (fail)
# output string(s) from glyph sequence

# test 3 (fail)
# decompose 5 MB JPEG, display glyph sequence, render same image on display

import transceiver

# test 1:
#payload = u"06349108765300123400000000123456789124"
beep_off = u"\u0080R0E0400."
factory_default = u"\u0080RD9FF50."
# payload is an ordinary string of size 512 bytes and length 491
payload = u"gloqmzwocvampmiqmimejltxgljqmauehpxkcfhnquljxhaojtvzamzbruofqkmbdlokpthlvsjmcbuefuvjltizcloyneppyubmuslycdnrctvmqmjqqxaseftrgbovohcfumiyzxyzgigotuzbdqofdhegsxbyyfwaelhhgzyoczixnxlrvqznqpemolpxljlwqchlwvwjgjaqanbocjdwmnhojdminwkddgtbljwwaxsgadlqiscpehllqjiupnumgdxlkaliogkwqpluvvrgxxzrwlkqsxzvurotoymoqetltgvobpatfhisszvtsjsbcbhrplbopnoffzgdjkcbpbpnnotxnjyysezkmgplcwczfraommjbxdkiitiweopkotjjxhwhtexhawzcoszvitramgsdwibtyflozyhlbeinudraxaczcotvhqydummeqkeqcpvvzodegtxaszkvqjlxhcrurayduqzasxf"
# decision: do not need to figure out how to import the functions from transceiver.py for now. May need to later.

# test creates list of init, payload, and end strings, calls function to encode and list objects, then calls function
# to render the glyphs
test1 = [
    transceiver.parameter_dictionary('Beep Off'),
    transceiver.parameter_dictionary('Scanning Mode Setting (Continue scanning)'),
    transceiver.parameter_dictionary('Reading Interval Time Setting (1000 ms)'),
    transceiver.parameter_dictionary('Image Stable Time Setting (100 ms)'),
    payload,
    transceiver.parameter_dictionary('Factory Default')
]

glyph_list = transceiver.encode_glyph_from_string(test1)
transceiver.display_glyph(glyph_list)


#transceiver.display_glyph(glyph_list)






# test 2:
# filename = u"/user/Downloads/daily_bread.jpg"
# Receive.decode_from_camera()
# Transmit().read_from_file(filename)

# test 3:
# small (401 B): /user/.ssh/id_rsa.pub
# medium (400.3 kB): /user/PycharmProjects/transceiver/Images/license.jpg
# large (5 MB): TODO: find 5 MB image

# def decode_encode():

































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




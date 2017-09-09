# test 1 (fail)
# display QR code sequence that contains init and payload strings

# test 2 (fail)
# output string(s) from QR code sequence

# test 3 (fail)
# decompose 5 MB JPEG, display QR code sequence, render same image on display

from transceiver import Transmit
from transceiver import Receive

# test 1:
# code = u"06349108765300123400000000123456789124"
# code1 = u"\u0080R0E0404."
# payload is an ordinary string of size 512 bytes and length 491
# payload = "gloqmzwocvampmiqmimejltxgljqmauehpxkcfhnquljxhaojtvzamzbruofqkmbdlokpthlvsjmcbuefuvjltizcloyneppyubmuslycdnrctvmqmjqqxaseftrgbovohcfumiyzxyzgigotuzbdqofdhegsxbyyfwaelhhgzyoczixnxlrvqznqpemolpxljlwqchlwvwjgjaqanbocjdwmnhojdminwkddgtbljwwaxsgadlqiscpehllqjiupnumgdxlkaliogkwqpluvvrgxxzrwlkqsxzvurotoymoqetltgvobpatfhisszvtsjsbcbhrplbopnoffzgdjkcbpbpnnotxnjyysezkmgplcwczfraommjbxdkiitiweopkotjjxhwhtexhawzcoszvitramgsdwibtyflozyhlbeinudraxaczcotvhqydummeqkeqcpvvzodegtxaszkvqjlxhcrurayduqzasxf"
# TODO: figure out how to import the functions from transmit.py and receive.py

# Transmit().encode_from_string(payload)
# Transmit().display_qr_from_file()  # step 2?

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




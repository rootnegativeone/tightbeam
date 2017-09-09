from qrtools import QR
import zbar

class Transmit:

    def __init__(self):
        pass

    def read_from_file(self, var1):
        myCode = QR(filename=var1)
        if myCode.decode():
            print myCode.data

    def decode_from_camera(self):

        # create a Processor
        proc = zbar.Processor()

        # configure the Processor
        proc.parse_config('enable')

        # initialize the Processor
        device = '/dev/video0'
        proc.init(device)

        # debug only: enable the preview window
        proc.visible = True

        # read at least one barcode (or until window closed)
        proc.process_one()

        # debug only: hide the preview window
        proc.visible = False

        # extract results
        for symbol in proc.results:
            # do something useful with results
            print symbol.data  # what was in this line before: print symbol.data

    def encode_from_string(self, var2):
        # prints to /tmp/... as a PNG file
        myCode = QR(data=var2)
        myCode.encode()
        print myCode.filename

    def display_qr_code(self):
        pass

'''
filename = u"/user/Downloads/daily_bread.jpg"
code = u"06349108765300123400000000123456789124"
code1 = u"\u0080R0E0404."
payload = "gloqmzwocvampmiqmimejltxgljqmauehpxkcfhnquljxhaojtvzamzbruofqkmbdlokpthlvsjmcbuefuvjltizcloyneppyubmuslycdnrctvmqmjqqxaseftrgbovohcfumiyzxyzgigotuzbdqofdhegsxbyyfwaelhhgzyoczixnxlrvqznqpemolpxljlwqchlwvwjgjaqanbocjdwmnhojdminwkddgtbljwwaxsgadlqiscpehllqjiupnumgdxlkaliogkwqpluvvrgxxzrwlkqsxzvurotoymoqetltgvobpatfhisszvtsjsbcbhrplbopnoffzgdjkcbpbpnnotxnjyysezkmgplcwczfraommjbxdkiitiweopkotjjxhwhtexhawzcoszvitramgsdwibtyflozyhlbeinudraxaczcotvhqydummeqkeqcpvvzodegtxaszkvqjlxhcrurayduqzasxf"

if __name__ == '__main__':

    #Transmit().read_from_file(filename)
    #Transmit().decode_from_camera()
    Transmit().encode_from_string(code1)
    #Transmit().display_qr_from_file()

#Transmit().encode_from_string(payload)
'''


'''

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

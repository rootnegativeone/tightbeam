import transceiver
import sys
import numpy

# test 1 (pass) -------------------------------------------------------------------------------------------------
# test creates list of init, payload, and end strings, calls function to encode and list objects, then calls function
# to render the glyphs

# test1 = [
#    transceiver.parameter_dictionary('Beep Off'),
#    transceiver.parameter_dictionary('Scanning Mode Setting (Continue scanning)'),
#    transceiver.parameter_dictionary('Reading Interval Time Setting (1000 ms)'),
#    transceiver.parameter_dictionary('Image Stable Time Setting (100 ms)'),
#] + transceiver.digest_payload(payload, 100) + [transceiver.parameter_dictionary('Factory Default')]

# payload = u"06349108765300123400000000123456789124"
# beep_off = u"\u0080R0E0400."
# factory_default = u"\u0080RD9FF50."

# Test 2 (pass) ----------------------------------------------------------------------------------------------------
# payload is an ordinary string of size 512 bytes and length 491
# payload = "gloqmzwocvampmiqmimejltxgljqmauehpxkcfhnquljxhaojtvzamzbruofqkmbdlokpthlvsjmcbuefuvjltizcloyneppyubmuslycdnrctvmqmjqqxaseftrgbovohcfumiyzxyzgigotuzbdqofdhegsxbyyfwaelhhgzyoczixnxlrvqznqpemolpxljlwqchlwvwjgjaqanbocjdwmnhojdminwkddgtbljwwaxsgadlqiscpehllqjiupnumgdxlkaliogkwqpluvvrgxxzrwlkqsxzvurotoymoqetltgvobpatfhisszvtsjsbcbhrplbopnoffzgdjkcbpbpnnotxnjyysezkmgplcwczfraommjbxdkiitiweopkotjjxhwhtexhawzcoszvitramgsdwibtyflozyhlbeinudraxaczcotvhqydummeqkeqcpvvzodegtxaszkvqjlxhcrurayduqzasxf"

# Test 3 (fail) ----------------------------------------------------------------------------------------------------
# extra small (RSA public key) <-- pass
#payload = open('/user/.ssh/id_rsa.pub', 'r')
#payload = payload.read()

# small (5 kb text file) <-- pass
#payload = open('/user/Downloads/test3small.txt', 'r')
#payload = payload.read()

# medium (50 kb image) <-- pass

filename = '/user/Pictures/dog.jpg'

import base64


def read_image(filename):
    with open(filename, "rb") as f:
        var = bytearray(f.read())
        payload = base64.b64encode(var)
        return payload

payload = read_image(filename)

# character length and string byte size
print "character length: " + str(len(payload))
print "size in bytes: " + str(sys.getsizeof(payload))

# insert payload list into position
test = transceiver.sequence_strings_for_encoding(payload)
for i in test:
    print i

# create list of glyphs encoded from string sequence
glyph_list = transceiver.encode_glyph_from_string(test)

# display glyphs in sequence
transceiver.display_glyph(glyph_list)

























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




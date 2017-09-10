

# ---------------------------------------------------------------------------------------------------------------
# Transmit
# TODO: parameter string dictionary
# TODO: string sequencer that sends QR codes for encoding

import pylab
import pyqrcode
# http://pythonhosted.org/PyQRCode/moddoc.html


def sequence_strings_for_encoding():
    # pull init strings from dictionary, save to list
    # add payload, save to list
    # pull end strings from dictionary, save to list
    pass


# TODO: method that encodes string to base64

# loops through list of strings to create list of glyph objects
glyph_list = []
def encode_glyph_from_string(text_list):
    for i in text_list:
        glyph_list.append(pyqrcode.create(i))
        # glyph.png('/user/Downloads/test_glyph_3.png', scale=6, quiet_zone=4) #  module_color=[0, 0, 0, 128], background=[0xff, 0xff, 0xcc])
    return glyph_list
    # TODO: loop through list of strings to generate list of glyph objects


# displays glyphs in list in sequence
def display_glyph(glyph_list):
    for index, values in enumerate(glyph_list):
        glyph_list[index].show(quiet_zone=4, scale=6, wait=1)

    # TODO: find better way of encoding and rendering glyphs (pyplot? something else?)
    # goal: loop through list of glyph objects and show each in the same window

# TODO: method to display QR code from base64
# png_as_base64_str(scale=1, module_color=(0, 0, 0, 255), background=(255, 255, 255, 255), quiet_zone=4)

def parameter_string_dictionary():
    pass


# ---------------------------------------------------------------------------------------------------------------
# Receive
# 1. trigger camera
# 2. read QR code (step 1 loop)
# 3. output string (step 2 loop)
# 4. append to list (step 3 loop)
# 5. concatenate strings
# 6. process strings (encode and render)

#output: payload or error codes

import zbar


def get_string_from_glyph_file(glyph):
    glyph = QR(filename=glyph)
    if glyph.decode():
        print glyph.data


def display_string(text):
    print text


def decode_QR_code_from_camera():
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
        return symbol.data

# TODO: create method for decoding barcodes from the camera
def decode_barcode_from_camera():
    pass
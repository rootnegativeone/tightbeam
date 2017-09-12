

# ---------------------------------------------------------------------------------------------------------------
# Transmit
# TODO: parameter string dictionary
# TODO: string sequencer that sends QR codes for encoding

import pylab
import pyqrcode
# http://pythonhosted.org/PyQRCode/moddoc.html


def sequence_strings_for_encoding():
    # pull init strings from dictionary, save to list
    # add payload, digest payload, save to list
    # pull end strings from dictionary, save to list
    pass


# TODO: break up long payload strings (>100 characters) in to sequence of glyphs
def digest_payload():
    # ingest long string (>100 characters)
    # split into 100 character strings
    # append to list of strings (iterable?)
    # return list of strings
    pass


# loops through list of strings to create list of glyph objects
glyph_list = []
def encode_glyph_from_string(text_list):
    for i in text_list:
        glyph_list.append(pyqrcode.create(i))
        # glyph.png('/user/Downloads/test_glyph_3.png', scale=6, quiet_zone=4) #  module_color=[0, 0, 0, 128], background=[0xff, 0xff, 0xcc])
    return glyph_list


# displays glyphs in list in sequence
def display_glyph(glyph_list):
    for index, values in enumerate(glyph_list):
        glyph_list[index].show(quiet_zone=4, scale=6, wait=1)
        print glyph_list[index]
    # TODO: find better way of encoding and rendering glyphs (pyplot? writeable stream?)
    # goal: loop through list of glyph objects and show each in the same window

# TODO: method that encodes string to base64 for pictures
# TODO: method to display QR code from base64 - convert PNG to base64
# png_as_base64_str(scale=1, module_color=(0, 0, 0, 255), background=(255, 255, 255, 255), quiet_zone=4)

# TODO: save one of the parameter strings as a QR code and read it using the IDE. Need to test with scanner.
# parameter string dictionary (init and end strings)
def parameter_dictionary(parameter):
    scanner_dict = {
        'Beep On': u"\u0080R0E0404.",
        'Beep Off': u"\u0080R0E0400.",
        'Factory Default': u"\u0080RD9FF50.",
        'Configuration Code ON': u"\u0080R030200.",
        'Configuration Code OFF': u"\u0080R030202.",
        'Configuration Code ON/OFF (Output content -disable)': u"\u0080R030100.",
        'Configuration Code ON/OFF (Output content -enable)': u"\u0080R030101.",
        'Aiming Setting (Normal mode)': u"\u0080R003010.",
        'Aiming Setting (Always on)': u"\u0080R003030.",
        'Aiming Setting (No aiming)': u"\u0080R003000.",
        'LED Light Setting (Normal mode)': u"\u0080R000C04.",
        'LED Light Setting (Always on)': u"\u0080R000C0C.",
        'LED Light Setting (No LED light)': u"\u0080R000C00.",
        'Scanning Mode Setting (Manual trigger)': u"\u0080R000300.",
        'Scanning Mode Setting (Continue scanning)': u"\u0080R000302.",
        'Scanning Mode Setting (Auto Sensing)': u"\u0080R000303.",
        'Reading Interval Time Setting (No interval)': u"\u0080R05FF00.",
        'Reading Interval Time Setting (500 ms)': u"\u0080R05FF05.",
        'Reading Interval Time Setting (1000 ms)': u"\u0080R05FF0A.",
        'Reading Interval Time Setting (1500 ms)': u"\u0080R05FF0F.",
        'Reading Interval Time Setting (2000 ms)': u"\u0080R05FF14.",
        'Single Scan Duration Setting (1000 ms)': u"\u0080R06FF0A.",
        'Single Scan Duration Setting (3000 ms)': u"\u0080R06FF1E.",
        'Single Scan Duration Setting (5000 ms)': u"\u0080R06FF32.",
        'Single Scan Duration Setting (No duration)': u"\u0080R06FF00.",
        'Image Stable Time Setting (100 ms)': u"\u0080R04FF01.",
        'Image Stable Time Setting (400 ms)': u"\u0080R04FF04.",
        'Image Stable Time Setting (1000 ms)': u"\u0080R04FF0A.",
        'Image Stable Time Setting (2000 ms)': u"\u0080R04FF14.",
    }
    return scanner_dict[parameter]


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
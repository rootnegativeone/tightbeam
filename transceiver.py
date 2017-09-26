
# TODO: have to figure out how to make this a class to instantiate objects for access by member functions
""" example
class Spam:
    def oneFunction(self,lists):
       category=random.choice(list(lists.keys()))
        self.word=random.choice(lists[category])

    def anotherFunction(self):
        for letter in self.word:
        print("_",end=" ")

Once you make a Class you have to Instantiate it to an Object and access the member functions.

s = Spam()
s.oneFunction(lists)
s.anotherFunction()
"""


# ---------------------------------------------------------------------------------------------------------------
# Transmit

import pyqrcode
import io
import gtk
import time
import imageio
import png

# http://pythonhosted.org/PyQRCode/moddoc.html

def sequence_strings_for_encoding(payload, size):
    # initialize empty string to hold list for encoding
    string_list = []

    # pull init strings from dictionary, save to list
    string_list.append(parameter_dictionary('Beep Off'))
    string_list.append(parameter_dictionary('Scanning Mode Setting (Continue scanning)'))
    string_list.append(parameter_dictionary('Reading Interval Time Setting (1000 ms)'))
    string_list.append(parameter_dictionary('Image Stable Time Setting (100 ms)'))
    #print string_list

    # add payload, digest payload, save to list
    for j in digest_payload(payload, size):
        string_list.append(j)

    # pull end strings from dictionary, save to list
    string_list.append(parameter_dictionary('Factory Default'))
    return string_list


def digest_payload(string, length):
    # ingest long string
    # split into smaller strings using length value passed in
    # create generator to loop through the smaller strings until the end
    # return list of smaller strings in generator
    generator = (string[0 + i:length + i] for i in range(0, len(string), length))
    for i in generator:
        yield i


# loops through list of strings to create list of glyph objects
def encode_glyph_from_string(string_list):
    glyph_list = []
    for i in string_list:
        glyph_list.append(pyqrcode.create(i))
        # glyph.png('/user/Downloads/test_glyph_3.png', scale=6, quiet_zone=4) #  module_color=[0, 0, 0, 128], background=[0xff, 0xff, 0xcc])
    return glyph_list


# TODO: find better way of encoding and rendering glyphs (riteable stream)
# purpose: loop through list of glyph objects and show each in the same window
def display_glyph(glyph_list):

    # create list for stream objects then loop through list of glyphs
    # encode PNG stream objects and save to list
    size_list = []
    png_stream_list = []
    for index, values in enumerate(glyph_list):
        # somehow show glyph_list[index] as SVG
        glyph = glyph_list[index]
        glyph_buffer = io.BytesIO()
        glyph.png(glyph_buffer, scale=5)
        # attempting to get PNG size to determine biggest
        size = glyph.get_png_size()
        size_list.append(size)
        png_stream = glyph_buffer.getvalue()
        png_stream_list.append(png_stream)

    max_png_size = max(size_list)
    max_png_size *= 5

    s = [[0 for y in range(max_png_size)] for x in range(max_png_size)]
    s = map(lambda x: map(int, x), s)

    f = open('/user/Downloads/png.png', 'wb')
    w = png.Writer(len(s[0]), len(s), greyscale=True, bitdepth=1)
    w.write(f, s)
    f.close()

    # to file: loop through PNG stream object list to create GIF and save to file
    with imageio.get_writer('/user/Downloads/test1.gif', mode='I', loop=0, fps=1) as writer:
        # add initial image to get correct size
        a = imageio.imread('/user/Downloads/png.png')
        writer.append_data(a)
        # loop through stream list
        for i in png_stream_list:
            i = imageio.imread(i)
            writer.append_data(i)

    # to bytestream: loop through PNG stream object list to create GIF stream object and return gif object in buffer
    # get values from gif object in buffer
    gif_buffer = io.BytesIO()
    with imageio.get_writer(gif_buffer, format='.gif', mode='?', loop=0, fps=15) as writer:
        for i in png_stream_list:
            i = imageio.imread(i)
            writer.append_data(i)

    gif_buffer = gif_buffer.getvalue()


    # create image buffer and send values from gif object to loader
    # close stream then create animation object
    pixbufanim = gtk.gdk.PixbufLoader()  # https://developer.gnome.org/pygtk/stable/class-gdkpixbufloader.html
    pixbufanim.write(gif_buffer)
    pixbufanim.close()
    pixbufanim = pixbufanim.get_animation()
    #pixbufanim = pixbufanim.get_iter()


    # open window, update the settings for that window, show it, then create and show the animation taken from
    # the animation object
    window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    window.set_title("transmission")
    window.set_position(gtk.WIN_POS_CENTER)
    window.set_border_width(10)
    window.show()
    image = gtk.Image()
    image.set_from_animation(pixbufanim)
    image.show()

    window.add(image)
    gtk.main()
    window.connect("delete-event", Gtk.main_quit)


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
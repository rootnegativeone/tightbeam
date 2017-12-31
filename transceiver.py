
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
# parameters
# string length for digesting longer strings
chunk = 150

# scale of encoded PNG
scale = 7

# frames per second in output GIF display
framerate = 15

# ---------------------------------------------------------------------------------------------------------------
# Transmit

import pyqrcode
import io
import gtk
import imageio
import base64

# http://pythonhosted.org/PyQRCode/moddoc.html


def digest_payload(string, length):
    # ingest long string
    # split into smaller strings using length value passed in
    # create generator to loop through the smaller strings until the end
    # return list of smaller strings in generator
    generator = (string[0 + i:length + i] for i in range(0, len(string), length))
    for i in generator:
        yield i


def read_image(filename):
    with open(filename, "rb") as f:
        var = bytearray(f.read())
        payload = base64.b64encode(var)
        return payload


def sequence_strings_for_encoding(payload):
    # print string length size, correlates to scanning duration
    print "chunk size: " + str(chunk)

    # initialize empty list to hold strings for encoding
    # first is for strings without indices
    string_list_no_index = []

    # second is meant to hold strings with added indices
    string_list = []

    # pull init strings from dictionary, save to list
    #string_list.append(parameter_dictionary('Beep Off'))
    #string_list.append(parameter_dictionary('Scanning Mode Setting (Continue scanning)'))
    #string_list.append(parameter_dictionary('Reading Interval Time Setting (500 ms)'))
    #string_list.append(parameter_dictionary('Single Scan Duration Setting (No duration)'))
    #string_list.append(parameter_dictionary('Image Stable Time Setting (100 ms)'))

    # iterate over payload generator to obtain strings and append to a list of strings
    for j in digest_payload(payload, chunk):
        #print j
        string_list_no_index.append(j)

    # iterate over list and merge index with values using 'enumerate()'
    # index should be four numbers starting from 0000 to 9999, so pad with zeros to the left with 'zfill()'
    # append results to empty string list
    for index, values in enumerate(string_list_no_index):
        padding = str(index).zfill(4)
        string_list.append(padding + values)

    # pull end strings from dictionary, save to list
    #string_list.append(parameter_dictionary('Factory Default'))

    payload_length = len(payload)
    print "Number of glyphs: " + str((payload_length/chunk) + (payload_length % chunk > 0))
    total_glyphs = "len=" + str((len(payload)/chunk) + (len(payload) % chunk > 0))
    string_list.append(total_glyphs)

    return string_list  # introduce randomness in index here for sampling later? ________________________


# loops through list of strings to create list of glyph objects
def encode_glyph_from_string(string_list):
    index = 0
    glyph_list = []
    #for index, values in enumerate(string_list):
    for values in string_list:
        glyph_list.append(pyqrcode.create(values))
        index += 1
        print "encoding: " + str(index)
        # glyph.png('/user/Downloads/test_glyph_3.png', scale=6, quiet_zone=4) #  module_color=[0, 0, 0, 128], background=[0xff, 0xff, 0xcc])
    return glyph_list


# purpose: loop through list of glyph objects and show each in the same window (i.e. stream to display)
# takes list of glyphs, writes to stream, creates PNGs,
def display_glyph(glyph_list):
    count = 0
    # create list for stream objects then loop through list of glyphs
    # encode PNG stream objects and save to list
    size_list = []
    png_stream_list = []
    for index, values in enumerate(glyph_list):
        # encode glyph_list[index] as PNG
        glyph = glyph_list[index]
        glyph_buffer = io.BytesIO()
        glyph.png(glyph_buffer, scale=int(scale))
        # attempting to get PNG size to determine biggest
        #size = glyph.get_png_size() #  <-- uncomment for GIF output
        #size_list.append(size) #<-- uncomment for GIF output
        png_stream = glyph_buffer.getvalue()
        png_stream_list.append(png_stream)
        count += 1
        print "rendering: " + str(count)

    # commented out but still necessary for GIF output
    '''
    # TODO: create function for pulling sizing PNG
    # TODO: import pyrcode.png scale variable as parameter for max PNG size value
    # pull largest PNG size and multiply by the scaling factor above
    max_png_size = max(size_list)
    max_png_size *= 7  # this comes from scale=7 above

    # inserts zeroes in matrix with x and y dimensions derived from the maximum PNG size generated from data
    # lambda expression that --- need to look up how this works
    s = [[0 for y in range(max_png_size)] for x in range(max_png_size)]
    s = map(lambda x: map(int, x), s)

    # creates PNG file "header" to set size of window properly for display
    # TODO: change from write to file to write to buffer
    f = open('/user/Downloads/png.png', 'wb')
    w = png.Writer(len(s[0]), len(s), greyscale=True, bitdepth=1)
    w.write(f, s)
    f.close()

    # TODO: change from read from file for PNG to read from buffer
    # TODO: find sample rate of hardware scanner (USB) - will handle serial in v2
    # to file: loop through PNG stream object list to create GIF and save to file
    with imageio.get_writer('/user/Downloads/test.gif', mode='I', loop=0, fps=15) as writer:
        # add initial image to get correct size
        a = imageio.imread('/user/Downloads/png.png')
        writer.append_data(a)
        # loop through stream list
        for i in png_stream_list:
            i = imageio.imread(i)
            writer.append_data(i)
    '''

    count = 0
    # TODO: add PNG as initial image to force correct window size
    # to bytestream: loop through PNG stream object list to create GIF stream object and return gif object in buffer
    # get values from gif object in buffer
    # camera frame sample rate is 30 frames per second; therefore, Nyquist frequency is 15 fps (0.5*sample rate).
    gif_buffer = io.BytesIO()
    with imageio.get_writer(gif_buffer, format='.gif', mode='?', loop=0, fps=int(framerate)) as writer:
        for i in png_stream_list:
            i = imageio.imread(i)
            writer.append_data(i)
            count += 1
            print "combining: " + str(count)

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

    print "Transmitting"
    window.add(image)
    gtk.main()

    window.connect("delete-event", Gtk.main_quit)



# TODO: method that encodes string to base64 for pictures
# TODO: method to display QR code from base64 - convert PNG to base64
# png_as_base64_str(scale=1, module_color=(0, 0, 0, 255), background=(255, 255, 255, 255), quiet_zone=4)

# TODO: save one of the parameter strings as a QR code and read it using the IDE. Need to test with hardware scanner.
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

import zbar
import qrtools
import cv2

# 1. trigger camera
# 2. read QR code (step 1 loop)
# 3. output string (step 2 loop)
# 4. append to list and/or yield (step 3 loop)
# 5. concatenate strings
# 6. process strings (encode and render)


def capture_frames_from_device():
    # open video device and save to capture variable
    capture = cv2.VideoCapture(0)

    # parse each frame of video and return in a sequence (list)
    while True:
        ret, frame = capture.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            cv2.imshow('frame', frame)
            scanner = zbar.Scanner()
            result = scanner.scan(frame)
            # if the results contain a string, yield use with generator object in another method
            if result:
                for i in result:
                    (yield i.data)

            if cv2.waitKey(10) & 0xFF == ord('q'): # this waitKey is necessary, transform to global variable
                break
        else:
            break

    capture.release()
    cv2.destroyAllWindows()
    # TODO: figure out a way to properly end this process above


# TODO: for debug, end printing if no new numbers seen in a while, concatenate strings and clean off index, return
# determine highest number of index and create progress indicator
# stop process when indicator shows all frames done


def prepare_decoded_strings_for_output():
    output_list = []

    # create generator object from capture_frames_from_device()
    output_generator = capture_frames_from_device()

    # iterate over generator object and append output to output_list
    for x in output_generator:
        # check if entry is not in list and append or keep looping going if it is in the list
        if x not in output_list:
            output_list.append(x)
            print str(len(set(output_list))) + ": " + x

        # check output length - may someday be replaced by some function that predicts the limit and removes "len="
        # could randomize in "transmitter.py" and use empirical Bayesian estimator for stochastic gradient descent
        if x[:4] == "len=" and len(set(output_list)) == (int(x[4:])+1):
            break
        else:
            continue

    # take output of this (set of output_list), sort from 0000 to highest, remove indices, join all strings, print
    # eliminate duplicate entries in glyph_data_list (set?)
    output = list(set(output_list))
    # sort from 0000 to highest
    output = sorted(output)
    # remove "len=" entry from list
    del output[-1]
    # remove indices
    output = [x[4:] for x in output]
    # join all items in list and print
    output = ''.join(output)
    print "length: " + str(len(output))
    print output
    #return output

    fh = open('/user/Pictures/test_dog.jpg', 'wb')
    fh.write(output.decode('base64'))
    fh.close()

# -----------------------------------------------------------------------------------------------------------------
# video = '/user/Downloads/test2.mp4'


def capture_frames_from_video(video):
    # import mp4 file from storage
    # parse each frame of video and return in a sequence (list)
    # https://stackoverflow.com/questions/18954889/how-to-process-images-of-a-video-frame-by-frame-in-video-streaming-using-opencv

    frame_list = []

    capture = cv2.VideoCapture(video)
    while True:
        ret, frame = capture.read()
        if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            # cv2.imshow('frame', frame)
            frame_list.append(frame)
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        else:
            break

    capture.release()
    cv2.destroyAllWindows()
    return frame_list


def decode_frames_into_strings(frame_list):
    glyph_data_list = []

    # loop through list of frames and decode them, then add them to a list, return that list
    for i, val in enumerate(frame_list):
        image = frame_list[i]
        scanner = zbar.Scanner()
        results = scanner.scan(image)
        for result in results:
            print "frame " + str(i), result.type, result.data, result.quality, result.position
            glyph_data_list.append(result.data)

    print glyph_data_list
    # eliminate duplicate entries in glyph_data_list (set?)
    glyph_data_list = set(glyph_data_list)
    # sort from 0000 to highest
    glyph_data_list = sorted(glyph_data_list)
    print glyph_data_list
    # remove indices
    glyph_data = [x[4:] for x in glyph_data_list]
    # join all items in list and print
    glyph_data = ''.join(glyph_data)
    print glyph_data
    print len(glyph_data)

'''
glyph = '/user/PycharmProjects/transceiver/QR Codes/payload.png'
def get_string_from_glyph_file(glyph):
    # get sequence of frames from video
    # decode QR one at a time
    glyph = qrtools.QR(filename='/user/PycharmProjects/transceiver/QR Codes/payload.png')
    if glyph.decode():
        print glyph.data

'''
# TODO: init string dictionary
# TODO: string sequencer that sends QR codes for encoding
# TODO: event that triggers displaying QR code sequence (GIF or dynamic display??)

from qrtools import QR


class Transmit:

    def __init__(self):
        pass

    def encode_from_string(self, x):
        # prints to /tmp/... as a PNG file
        myCode = QR(data=x)
        myCode.encode()
        print myCode.filename

    def display_qr_code_from_string(self, var3):
        # read from file
        new_string = var3
        pass
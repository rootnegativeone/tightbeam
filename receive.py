# receiver app (merchant)
# 1. trigger camera
# 2. read QR code (step 1 loop)
# 3. output string (step 2 loop)
# 4. append to list (step 3 loop)
# 5. concatenate strings
# 6. process strings (encode and render)

#output: payload or error codes

from qrtools import QR
import zbar


class Receive:

    def __init__(self):
        pass

#for testing purposes, need a method to
def get_string_from_QR_code(self, var1):
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

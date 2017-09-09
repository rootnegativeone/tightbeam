from transceiver import Transmit


filename = u"/user/Downloads/daily_bread.jpg"
code = u"06349108765300123400000000123456789124"
code1 = u"\u0080R0E0404."

#payload is an ordinary string of size 512 bytes and length 491
payload = "gloqmzwocvampmiqmimejltxgljqmauehpxkcfhnquljxhaojtvzamzbruofqkmbdlokpthlvsjmcbuefuvjltizcloyneppyubmuslycdnrctvmqmjqqxaseftrgbovohcfumiyzxyzgigotuzbdqofdhegsxbyyfwaelhhgzyoczixnxlrvqznqpemolpxljlwqchlwvwjgjaqanbocjdwmnhojdminwkddgtbljwwaxsgadlqiscpehllqjiupnumgdxlkaliogkwqpluvvrgxxzrwlkqsxzvurotoymoqetltgvobpatfhisszvtsjsbcbhrplbopnoffzgdjkcbpbpnnotxnjyysezkmgplcwczfraommjbxdkiitiweopkotjjxhwhtexhawzcoszvitramgsdwibtyflozyhlbeinudraxaczcotvhqydummeqkeqcpvvzodegtxaszkvqjlxhcrurayduqzasxf"

if __name__ == '__main__':

    #Transmit().read_from_file(filename)
    #Transmit().decode_from_camera()
    Transmit().encode_from_string(code1)
    #Transmit().display_qr_from_file()

#Transmit().encode_from_string(payload)

# test test test 12 12 12 tap tap tap is this thing on?
import pyfirmata
import serial
import sys
import time
import threading

import matplotlib.pyplot as plt

DEBUG = False
VERBOSE = False  # Verbose mode provides more raw EEG updates
MINDFLEX_PORT = '/dev/cu.MINDFLEX-DevB'
ARDUINO_PORT = '/dev/tty.usbmodem14101'

TRIGGER_MIN = 50

MAX_PACKET_LEN = 169

# Switch the Mindflex headset mode to 0x02
RESET_CODE = ['\x00', '\xF8', '\x00', '\x00', '\x00', '\xE0']  # RESET_CODE = '\x00\xF8\x00\x00\x00\xE0'.encode()


def _cb(data):
    print(data)
    if len(data) == 1:
        return

    value = data['attention']
    eeg.append(value)
    if len(eeg) > 50:
        eeg.pop(0)

    line.set_ydata(eeg)
    plt.pause(1)

    if value >= TRIGGER_MIN:
        x = threading.Thread(target=trigger)
        x.start()


def mf_parser(packet):
    # See the MindSet Communications Protocol
    ret = {}
    # The first byte in the list was packet_len, so start at i = 1
    i = 1
    while i < len(packet) - 1:
        code_level = ord(packet[i])

        # signal quality
        if code_level == 0x02:
            ret['quality'] = ord(packet[i + 1])
            i += 2
        # attention
        elif code_level == 0x04:
            ret['attention'] = ord(packet[i + 1])
            i += 2
        # meditation
        elif code_level == 0x05:
            ret['meditation'] = ord(packet[i + 1])
            i += 2
        # EEG power
        elif code_level == 0x83:
            ret['eeg'] = []
            for c in range(i + 1, i + 25, 3):
                ret['eeg'].append(ord(packet[c]) << 16 |
                                  ord(packet[c + 1]) << 8 |
                                  ord(packet[c + 2]))
            i += 26
        # Raw Wave Value
        elif code_level == 0x80:
            ret['eeg_raw'] = ord(packet[i + 1]) << 8 | ord(packet[i + 2])
            i += 4
        else:
            i += 1

    return ret


class MindFlexConnection(object):
    def __init__(self, port=MINDFLEX_PORT, debug=DEBUG, verbose=VERBOSE):
        self.debug = debug
        self.verbose = verbose
        self.ser = serial.Serial(port=port, baudrate=57600)
        print('Connection open')
        if self.debug:
            self.received = []

    def close(self):
        if self.ser.isOpen():
            try:
                self.ser.close()
                if self.debug:
                    print(self.received)
            except Exception as e:
                pass
            print('Connection closed')

    def switchMode(self):
        if self.debug:
            print('Setting Mode 2')

        # Send reset code
        for c in RESET_CODE:
            for i in range(6):
                self.ser.write(c.encode())
        # self.ser.write(RESET_CODE)
        time.sleep(.001)

    def read(self, callback=_cb):
        prev_byte = 'c'
        in_packet = False
        try:
            while True:
                cur_byte = self.ser.read(1)
                if self.debug:
                    print(cur_byte)
                    self.received.append(cur_byte)

                # If in Mode 1, enable Mode 2
                if not in_packet and ord(prev_byte) == 224 and ord(cur_byte) == 224:
                    self.switchMode()
                    if self.debug and ord(self.ser.read(1)) != 224:
                        print('Mode 2 enabled')
                        prev_byte = cur_byte
                        continue

                # Look for the start of the packet
                if not in_packet and ord(prev_byte) == 170 and ord(cur_byte) == 170:
                    in_packet = True
                    packet = []
                    continue

                if in_packet:
                    if len(packet) == 0:
                        if ord(cur_byte) == 170:
                            continue
                        packet_len = ord(cur_byte)
                        checksum_total = 0
                        packet = [cur_byte]
                        if packet_len >= MAX_PACKET_LEN:
                            print('Packet too long: %s' % packet_len)
                            in_packet = False
                            continue

                    elif len(packet) - 1 == packet_len:
                        packet_checksum = ord(cur_byte)
                        in_packet = False
                        if (~(checksum_total & 255) & 255) == packet_checksum:
                            try:
                                if self.verbose or packet_len > 4:
                                    ret = mf_parser(packet)
                                    if self.debug:
                                        print(ret)
                                    callback(ret)
                            except Exception as e:
                                print('Could not parse because of %s' % e)
                        else:
                            print('Warning: invalid checksum')
                            print(~(checksum_total & 255) & 255)
                            print(packet_checksum)
                            print(packet)
                    else:
                        checksum_total += ord(cur_byte)
                        packet.append(cur_byte)

                # keep track of last byte to catch sync bytes
                prev_byte = cur_byte

        except KeyboardInterrupt as e:
            self.close()
            if self.debug:
                print('Exiting')
            sys.exit(0)


def createGraph():
    eeg = [0] * 50

    plt.ion()

    fig, ax = plt.subplots(1, 1)
    ax.set_xlim([0, 50])
    ax.set_ylim([0, 100])
    line, = ax.plot(eeg)
    plt.ylabel('EEG values')
    plt.xlabel('Time')

    plt.show(block=False)
    plt.pause(2)

    return eeg, line


def trigger():
    pass


if __name__ == '__main__':
    eeg, line = createGraph()
    print("Created Graph")

    arduino = pyfirmata.Arduino(ARDUINO_PORT)

    connection = MindFlexConnection()
    connection.read()

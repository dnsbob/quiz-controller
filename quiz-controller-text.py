#!/usr/bin/env python3
'''
quiz controller, text version
'''

############# ***** NEXT - DECIPHER CONTROLLER INPUT ****

import time
import serial

# from https://stackoverflow.com/questions/2408560/non-blocking-console-input
import sys
import select
import tty
import termios

class NonBlockingConsole(object):

    def __enter__(self):
        self.old_settings = termios.tcgetattr(sys.stdin)
        tty.setcbreak(sys.stdin.fileno())
        return self

    def __exit__(self, type, value, traceback):
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.old_settings)


    def get_data(self):
        if select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], []):
            return sys.stdin.read(1)
        return False


class Usbserial(object):
    def __enter__(self):
        # serial setup
        SERIALPORT = "/dev/ttyACM0"
        BAUDRATE = 115200
        while True:
            try:
                self.ser = serial.Serial(SERIALPORT, BAUDRATE)
                print("\n\n")
                return self
            except FileNotFoundError as e:
                print(f"waiting on port {SERIALPORT}:{e}",end="\r")
            except serial.serialutil.SerialException as e:
                print(f"waiting for {SERIALPORT}:{e}",end="\r")
            time.sleep(1)
        

    def __exit__(self, type, value, traceback):
        self.ser.close()

    def get_data(self):
        cnt=self.ser.in_waiting
        if cnt:
            return self.ser.readline(cnt)
        return None


def main():
    '''quiz-controller-text'''
    # setup
    keys="1234567890!@#$%^&*() \n<>,."
    max=10 # update keys above if this changes
    player=[]   # list of player status
    enable=[]   # enable status of player
    for i in range(max):
        print("player",i,"is key",keys[i])
        player.append(False)    # false=seated, true=standing
        enable.append(True)



    # test
    player[3]=1

    # main loop
    with NonBlockingConsole() as nbc:
        with Usbserial() as myusb:
            while True:
                # read controller
                c=myusb.get_data()
                if c:
                    print(f"from controller:{c}:")
                # print
                print("\r",end="")
                for i in range(max):
                    playernum=i+1
                    if enable[i]:
                        if player[i]:
                            symbol="*"
                        else:
                            symbol=" "
                    else:
                        symbol="_"
                    print(f" {symbol}{playernum}{symbol} ",end="")
                #print()
                # read keyboard
                c=nbc.get_data()
                if c:
                    try:
                        j=keys.index(c)
                    except ValueError as e:
                        print(f"key {c} not understood")
                        c=""
                if c:
                    if j<max:
                        # toggle seat enable/disable
                        if enable[j]:
                            enable[j]=False
                        else:
                            enable[j]=True
                    elif j<2*max:
                        # pretend seat went True
                        player[j-max]=True
                time.sleep(.1)


if __name__ == "__main__":
    main()

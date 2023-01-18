#!/usr/bin/env python3
'''
quiz controller, text version
'''

import time
import serial
import re

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
        self.buf=b""
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
            self.buf=self.buf+self.ser.readline(cnt)
            if b"\n" in self.buf:
                i=self.buf.index(b"\n")
                line=self.buf[0:i+1]
                self.buf=self.buf[i+1:]
                return line
        return None


def chkstand(pin,state,enable,stand,standing):
    '''update stand list'''
    if state == False and enable == True:
        stand.append(pin+1)
    else:
        try:
            stand.remove(pin+1)
        except ValueError as e:
            pass   # this is expected
            #print(f'error - {pin+1} not in {stand}')
    if len(stand) > 0:
        standing=stand[0]
    else:
        standing=-1
    return standing


def main():
    '''quiz-controller-text'''
    # setup
    keys="1234567890!@#$%^&*() \n<>,."
    max=10 # update keys above if this changes
    player=[]   # list of player status
    enable=[]   # enable status of player
    for i in range(max):
        print(f"player {i+1} is key {keys[i]}")
        player.append(True)    # True=seated, False=standing
        enable.append(True)
    stand=[]    # ordered list of players that stood up
    standing=-1


    # main loop
    with NonBlockingConsole() as nbc:
        with Usbserial() as myusb:
            while True:
                # read controller
                c=myusb.get_data()
                if c:
                    s=c.decode()
                    #print(f"from controller:{c}:")
                    m=re.match(r'pin (\d+) (True|False) ',s)
                    pin=int(m[1])
                    state=eval(m[2])
                    if state:
                        pos="seated"
                    else:
                        pos="STANDING"
                    if m:
                        print(f'player {pin+1} {pos}')
                        print() # blank line
                    else:
                        print('not decoded')
                    if player[pin] != state:
                        player[pin]=state
                    standing=chkstand(pin,state,enable[pin],stand,standing)
                    #print(f'stand: {stand}, standing: {standing}')

                else:
                    time.sleep(.1)  # only sleep if no input

                # print the main output line
                print("\r",end="")
                for i in range(max):
                    playernum=i+1
                    if playernum == standing:
                        symbol="*"
                    elif enable[i]:
                        if player[i]:
                            symbol=" "
                        else:
                            symbol="."
                    else:
                        symbol="_"
                    print(f" {symbol}{playernum}{symbol} ",end="")
                print(f'    first: {standing}   standing: {stand}   ',end="")
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
                        #print(f"pin {j} state {player[j]} enable {enable[j]} stand {stand}")
                        standing=chkstand(j,player[j],enable[j],stand,standing)
                        #print(f'stand: {stand}, standing: {standing}')
                    elif j<2*max:
                        # toggle seat value - for testing
                        if player[j-max]:
                            player[j-max]=False
                        else:
                            player[j-max]=True
                    elif c==" ":
                        for j in range(max):
                            player[j]=True
                        stand=[]
                        print("reset")
                    elif c=="\n":
                        '''enter is go button'''
                        #stand=[]
                    else:
                        print(f"char not found:{c}")


if __name__ == "__main__":
    main()

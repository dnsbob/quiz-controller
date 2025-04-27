#!/usr/bin/env python3
'''
quiz controller, text version
'''

import time
import serial
import re
from pygame import mixer

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
                print(f" waiting on port {SERIALPORT}:{e}",end="\r")
            except serial.serialutil.SerialException as e:
                print(f" waiting for {SERIALPORT}:{e}",end="\r")
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


def chkstand(pin,state,enable,stand):
    '''update stand list'''
    #print(f" chkstand pin={pin} sit={state} enable={enable}") ## debug
    if state == False and enable == True:
        stand.append(pin+1)
    else:
        try:
            stand.remove(pin+1)
        except ValueError as e:
            pass   # this is expected
            #print(f' error - {pin+1} not in {stand}')
    if len(stand) > 0:
        newstanding=stand[0]
    else:
        newstanding=-1
    return newstanding


def updplayer(pin,state,playerstatus,beep):
    '''update player'''
    if state:
        pos="seated"
    else:
        pos="STANDING"
    print(f' player {pin+1} {pos}')
    #print() # blank line
    if playerstatus[pin] != state:
        playerstatus[pin]=state
        if pos == "STANDING":
            beep=True
    return beep


def main():
    '''quiz-controller-text'''
    # setup
    mixer.init()
    sound=mixer.Sound("beep-2.wav")
    #print(time.monotonic())
    sound.play()
    #print(time.monotonic())
    keys="1234567890!@#$%^&*() \n"
    max=10 # update keys above if this changes
    players=[]  # everything about each player
    playerstatus=[]   # list of player status
    playernew=[]    # debounce new value
    enable=[]   # enable status of player
    enablenew=[]    # debounce new value
    bounce=[]   # last change time of player, time.monotonic()
    for i in range(max):
        print(f"player {i+1} is key {keys[i]}")
        player={}   # all about one player
        player['sit']=True
        player['enable']=True
        player['sitnew']=True
        player['enablenew']=True
        player['lastchg']=time.monotonic()
        playerstatus.append(True)    # True=seated, False=standing
        playernew.append(True)
        enable.append(True)
        enablenew.append(True)
        bounce.append(0)        # time of next change
    stand=[]    # ordered list of players that stood up
    standing=-1
    beep=False
    bouncetime=.2  # debounce players and switches until no change for bounce time
    bouncelist=[]  # list of players in bounce time
    bounceend=0    # end of bounce for first player in bouncelist, or zero if list is empty
    

    # main loop
    with NonBlockingConsole() as nbc:
        with Usbserial() as myusb:
            while True:
                # read controller
                c=myusb.get_data()
                if c:
                    s=c.decode()
                    print(f" from controller:{c}:")  ## debug
                    m=re.match(r'pin (\d+) (True|False) ',s)
                    if m:
                        pin=int(m[1])
                        state=eval(m[2])
                        if state == playerstatus[pin]:
                            print(f' player {pin+1} already {state}')
                        else:
                            beep=updplayer(pin,state,playerstatus,beep)
                            standing=chkstand(pin,state,enable[pin],stand)
                            #print(f' stand: {stand}, standing: {standing}')
                    else:
                        print(' usb not decoded: ',s)
                else:
                    if beep:
                        #print(" BEEP")
                        #print(time.monotonic())
                        sound.play()
                        #print(time.monotonic())
                        beep=False
                    time.sleep(.1)  # only sleep if no input

                # print the main output line
                print("\r",end="")
                for i in range(max):
                    playernum=i+1
                    if playernum == standing:
                        symbol="*"  # the first one standing currently
                    elif enable[i]:
                        if playerstatus[i]:
                            symbol=" "  # seated - number toggles enable
                        else:
                            symbol="."  # standing but not first
                    else:
                        symbol="_" # disabled - number toggles enable
                    print(f" {symbol}{playernum}{symbol} ",end="")
                print(f'    first: {standing}   standing: {stand}   ',end="")
                #print(f' beep={beep}   ',end="")
                #print(time.clock_gettime_ns(2))
                print(time.monotonic(),end="")
                #print()

                # read keyboard
                c=nbc.get_data()
                if c:
                    try:
                        j=keys.index(c)
                    except ValueError as e:
                        print(f"  key {c} not understood")
                        c=""
                if c:
                    if j<2*max:
                        if j<max:
                            pin=j
                            # toggle seat enable/disable
                            if enable[pin]:
                                enable[pin]=False
                            else:
                                enable[pin]=True
                            #print(f" pin {j} state {playerstatus[j]} enable {enable[j]} stand {stand}")
                            standing=chkstand(pin,playerstatus[pin],enable[pin],stand)
                            #print(f' stand: {stand}, standing: {standing}')
                        else: # j<2*max:
                            pin=j-max
                            # toggle seat value - for testing
                            if playerstatus[pin]:
                                playerstatus[pin]=False
                            else:
                                playerstatus[pin]=True
                            standing=chkstand(pin,playerstatus[pin],enable[pin],stand)
                        state=playerstatus[pin]    
                        notbeep=updplayer(pin,state,playerstatus,beep)
                    elif c==" ":
                        for j in range(max):
                            playerstatus[j]=True
                        stand=[]
                        standing=-1
                        print("  reset")
                    elif c=="\n":
                        '''enter is go button'''
                        #stand=[]
                    else:
                        print(f" char not found:{c}")


if __name__ == "__main__":
    main()

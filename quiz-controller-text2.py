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

# global vars
bouncetime=2  # debounce players and switches until no change for bounce time (.2)
bouncechk=1  # how often to check for bounce end (.1)

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


def chkstand(state,standlist,player):
    '''update 'standlist' list of who is standing and in what order, also returns the first person'''
    print(f" chkstand state={state} standlist={standlist} player={player}") ## debug
    pin=player['pin']
    playernum=pin+1
    enable=player['enable']
    if state == False and enable == True:
        if playernum not in standlist:
            standlist.append(playernum)
    else:
        try:
            standlist.remove(playernum)
        except ValueError as e:
            pass   # this is expected
            #print(f' error - {pin+1} not in {standlist}')
    if len(standlist) > 0:
        newstanding=standlist[0]
    else:
        newstanding=-1
    return newstanding


def updplayer(state,timenow,beep,player,bouncelist):
    '''update player'''
    pin=player['pin']
    playernum=pin+1
    oldstate=player['sit'] # players current debounced state
    if state:
        pos="seated"
    else:
        pos="STANDING"
    if timenow > 0:
        print(f' player {playernum} {pos}')
        if player['sitnew'] != state:
            player['sitnew']=state
            #print(f"in updplayer, {player}")
            if timenow > player['lastchg'] + bouncetime:
                player['sit']=player['sitnew']
            else:
                if playernum not in bouncelist:
                    bouncelist.append(playernum)
            player['lastchg'] = timenow
    else: # timenow=0
        player['sit']=player['sitnew']
        if playernum in bouncelist:
            bouncelist.remove(playernum)
    if oldstate and not player['sit']: # if player was considered sitting, but is now standing, beep
        beep=True   # beep might already be set, so do not clear it, just set it
    return beep


def main():
    '''quiz-controller-text'''

    # setup
    mixer.init()
    sound=mixer.Sound("beep-2.wav")
    sound.play()
    keys="1234567890!@#$%^&*() \n"
    max=10 # update keys above if this changes
    players=[]  # everything about each player - list of player objects
    for i in range(max):
        print(f"player {i+1} is key {keys[i]}")
        player={}   # dict obj - all about one player
        player['pin']=i # pin number (playernum = pin + 1)
        player['sit']=True # the debounced state
        player['enable']=True
        player['sitnew']=True	# if bouncing, update here and not 'sit', this is the actual state
        #player['enablenew']=True
        player['lastchg']=0 # used to determine bouncing  (time.monotonic(), timenow)
        players.append(player)
    standlist=[]    # ordered list of players that are standing, in the order they stood up
    standing=-1
    beep=False
    notbeep=False # for keyboard override, do not beep
    bouncelist=[]  # list of players in bounce time
    bounceend=0    # end of bounce for first player in bouncelist, or zero if list is empty
    bounceend=time.monotonic() + bouncechk
    

    # main loop
    with NonBlockingConsole() as nbc:
        with Usbserial() as myusb:
            while True:
                timenow=time.monotonic()
                # read controller, typical data is "pin 1 False 15.9609", "pin 1 True 16.1797"
                c=myusb.get_data()
                if c: # data from controller 
                    s=c.decode()    # bytes to string (utf)
                    print(f" from controller:{c}: ",end="")  ## debug
                    #m=re.match(r'pin (\d+) (True|False) ([0-9.]+)',s)
                    m=re.match(r'pin (\d+) (True|False)',s)
                    if m:
                        pin=int(m[1])
                        state=eval(m[2])
                        player=players[pin]
                        #print(f" pin {pin} state {state} timenow {timenow} player {player}  ")  # debug
                        if state == player['sitnew']:
                            print(f' player {pin+1} already {state}')
                        else:
                            beep=updplayer(state,timenow,beep,player,bouncelist)
                            standing=chkstand(player['sit'],standlist,player)
                    else:
                        print(' usb not decoded: ',s)
                else: # no input, we have time to do other things
                    if bounceend > 0 and timenow > bounceend:
                        bounceend=0
                        for i in range(max):
                            player=players[i]
                            oldstate=player['sit']
                            if player['sitnew'] != oldstate:    # player in bounce mode and not same as first
                                if player['lastchg'] + bouncetime < timenow:
                                    #chgtime=0
                                    #state=player['sitnew']
                                    #beep=updplayer(state,chgtime,beep,player,bouncelist)
                                    
                                    if timenow > player['lastchg'] + bouncetime:
                                        state=player['sitnew']
                                        if state:
                                            pos="seated"
                                        else:
                                            pos="STANDING"
                                        player['sit']=state
                                        print(f"  player {player['pin']+1} debounce to {pos}  ",end="")
                                        chgtime=0
                                        beep=updplayer(state,chgtime,beep,player,bouncelist)
                                        standing=chkstand(player['sit'],standlist,player)
                                    #if oldstate and not player['sit']: # if player was considered sitting, but is now standing, beep
                                    #    beep=True   # beep might already be set, so do not clear it, just set it
                                else:
                                    if bounceend:
                                        bounceend = min(bounceend,player['lastchg'] + bouncetime)
                                    else: # bounceend is zero
                                        bounceend = player['lastchg'] + bouncetime
                        bounceend=time.monotonic() + bouncechk
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
                    player=players[i]
                    playernum=i+1
                    if playernum == standing:
                        symbol="*"  # the first one standing currently
                        #elif enable[i]:  
                    elif player['enable']:
                        if player['sit']:
                            #if playerstatus[i]:
                            symbol=" "  # seated - number toggles enable
                        else:
                            symbol="."  # standing but not first
                    else:
                        symbol="_" # disabled - number toggles enable
                    print(f" {symbol}{playernum}{symbol} ",end="")
                print(f'    first: {standing}   standlist: {standlist}   bouncelist: {bouncelist}   ',end="")
                #print(f' beep={beep}   ',end="")
                print(f"bounceend {bounceend}   ",end="")
                #print(time.clock_gettime_ns(2))
                print(timenow,end="")
                #print()

                # read keyboard
                c=nbc.get_data()
                if c:
                    try:
                        j=keys.index(c)
                        print(f' key # {j} ',end='')    # debug
                    except ValueError as e:
                        print(f"  char# {ord(c)} not understood")
                        c=""
                if c:
                    if j<2*max:
                        if j<max:   # 1-9,0  enable/disable seat
                            pin=j
                            player=players[j]
                            # toggle seat enable/disable
                            if player['enable']:
                                player['enable']=False
                            else:
                                player['enable']=True
                            standing=chkstand(player['sit'],standlist,player)
                            #print(f' standlist: {standlist}, standing: {standing}')
                        else: # j<2*max:  # shift 1-9,0 (punctuation) - toggle seat value
                            pin=j-max
                            print(f' pin {pin} ',end='')   # debug
                            player=players[pin]
                            # toggle seat value - for testing
                            if player['sit']:
                                player['sit']=False
                            else:
                                player['sit']=True
                            standing=chkstand(player['sit'],standlist,player)
                        state=player['sit']
                        chgtime=0
                        notbeep=updplayer(state,chgtime,notbeep,player,bouncelist)
                    elif c==" ": # space = reset
                        for j in range(max):
                            players[j]['sit']=True
                        standlist=[]
                        standing=-1
                        print("  reset")
                    elif c=="\n": # enter = show status of each player
                        '''enter is go button'''
                        #standlist=[]
                        # debug - show player data
                        for j in range(max):
                            player=players[j]
                            print(player)
                    # can add more keyboard functions above this line
                    else:
                        print(f" char not found:{c}")


if __name__ == "__main__":
    main()

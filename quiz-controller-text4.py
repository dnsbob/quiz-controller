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
bouncetime=.5  # debounce players and switches until no change for bounce time
positions={True: 'seated', False: 'STANDING'}
bounceend=0    # end of bounce for first player in bouncelist, or zero if list is empty
players={}
debug=0
readytime=0
readywait=2 # all players seated for this long to play ready sound
timenow=0

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
    if debug:
        print(f" chkstand state={state} standlist={standlist} player={player}") ## debug
    global readytime
    global timenow
    playernum=player['playernum']
    enable=player['enable']
    if state == False and enable == True:
        if playernum not in standlist:
            standlist.append(playernum)
            readytime=0
    else:
        if playernum in standlist:
            standlist.remove(playernum)
            if not standlist:   # list just became empty
                readytime=timenow + readywait
    if len(standlist) > 0:
        newstanding=standlist[0]
    else:
        newstanding=-1
    return newstanding


def updplayer(state,timenow,beep,player,bouncelist):
    '''update player and bouncelist, return beep'''
    playernum=player['playernum']
    oldsit=player['sit'] # players current debounced state
    oldsitnew=player['sitnew'] # players current actual state
    global bounceend
    global players
    if debug:
        print(f"  updplayer state {state}  timenow {timenow:.2f} {player} ")
    if player['sitnew'] != state:   # update sitnew, always the current position
        player['sitnew']=state
        #print(f"in updplayer, {player}")
    if timenow == 0:
        print(f" FAILED - time is zero  ")
    if timenow > player['lastchg'] + bouncetime: # not bouncing
        player['sit']=player['sitnew']
        print(f"  player {playernum} now {positions[state]}  stable")
        if playernum in bouncelist:
            bouncelist.remove(playernum)
    else: # bouncing
        print(f"  player {playernum} is {positions[state]}  bouncing  ")
        if playernum not in bouncelist:
            bouncelist.append(playernum)
    if bouncelist:
        bounceplayernum=bouncelist[0] # first in list is the soonest to debounce
        bounceplayer=players[bounceplayernum]
        bounceend=bounceplayer['lastchg'] + bouncetime
    else:
        bounceend=0

    if oldsitnew != player['sitnew']:  # only update lastchg if actual position changed, not when debouncing
        player['lastchg'] = timenow
   
    if oldsit and not player['sit']: # if player was considered sitting, but is now standing, beep
        beep=True   # beep might already be set, so do not clear it, just set it
    return beep


def main():
    '''quiz-controller-text'''
    global timenow

    # setup
    mixer.init()
    readysound=mixer.Sound("tada-fanfare-a-6313.mp3")
    readysound.play()
    time.sleep(1) # give it time to play
    beepsound=mixer.Sound("beep-2.wav")
    beepsound.play()
    keys="1234567890!@#$%^&*() \n"
    max=10 # update keys above if this changes, number of players
    global readytime  # all players seated for readywait time
    global players # everything about each player - dict of player objects, key in playernum
    pin2playernum={}    # dict - key is pin number, value is playernum
    for i in range(max):
        pin=i
        keyindex=i
        playernum=pin+1
        print(f"player {playernum} is key {keys[keyindex]}")
        player={}   # dict obj - all about one player
        pin2playernum[i]=playernum    
        player['pin']=pin
        player['playernum']=playernum
        player['sit']=True # the debounced state
        player['enable']=True   # can disable players
        player['sitnew']=True	# if bouncing, update here and not 'sit', this is the actual state
        player['lastchg']=0 # used to determine bouncing  (time.monotonic(), timenow)
        players[playernum]=player # add to dict
    standlist=[]    # ordered list of playernum that are standing, in the order they stood up
    standing=-1     # playernum of first player standing, or -1 if none
    beep=False      # True if any player has just stood up and beep sound has not played yet
    notbeep=False # for keyboard override, do not beep
    bouncelist=[]  # list of playernum in bounce time
    global bounceend
    

    # main loop
    with NonBlockingConsole() as nbc:
        with Usbserial() as myusb:
            while True:
                timenow=time.monotonic()
                # read controller, typical data is "pin 1 False 15.9609", "pin 1 True 16.1797"
                c=myusb.get_data()
                if c: # data from controller 
                    s=c.decode()    # bytes to string (utf)
                    if debug:
                        print(f" from controller:{c}: ",end="")  ## debug
                    #m=re.match(r'pin (\d+) (True|False) ([0-9.]+)',s) # controller has a time value, but we do not use it
                    m=re.match(r'pin (\d+) (True|False)',s)
                    if m:
                        pin=int(m[1])
                        playernum=pin2playernum[pin]
                        state=eval(m[2])
                        player=players[playernum]
                        #print(f" pin {pin} state {state} timenow {timenow} player {player}  ")  # debug
                        # note - call these even if state is same as previous state
                        beep=updplayer(state,timenow,beep,player,bouncelist)
                        standing=chkstand(player['sit'],standlist,player)
                    else:
                        print(' usb not decoded: ',s)
                else: # no input, we have time to do other things
                    # new bounceend with bouncelist
                    if bounceend and timenow > bounceend:
                        if debug:
                            print(f"  debounce  bounceend {bounceend} timenow {timenow}  ")
                        # just handle the first player each time
                        playernum=bouncelist[0]
                        player=players[playernum]
                        state=player['sitnew']
                        if debug:
                            print(f"  player {playernum} debounce to {positions[state]}  ",end="")
                        beep=updplayer(state,timenow,beep,player,bouncelist)
                        standing=chkstand(player['sit'],standlist,player)

                    if beep:
                        print(" BEEP ")
                        #print(time.monotonic())
                        beepsound.play()
                        #print(time.monotonic())
                        beep=False
                    
                    if readytime and timenow > readytime:
                        readytime=0
                        readysound.play()
                        print(f" READY ")
                    
                    time.sleep(.1)  # only sleep if no input

                # print the main output line
                print("\r",end="")
                for i in range(max):
                    playernum=i+1
                    player=players[playernum]
                    if player['enable']:
                        if player['sit']:
                            symbol=" "  # seated - number toggles enable
                        elif playernum == standing:
                            symbol="*"  # the first one standing currently
                        else:
                            symbol="."  # standing but not first
                    else:
                        symbol="_" # disabled - number toggles enable
                    print(f" {symbol}{playernum}{symbol} ",end="")
                print(f" time {timenow:9.2f}     stand {standlist} \t bounce {bouncelist}\t {bounceend:9.2f} ",end='')
                #print(f" stand {standlist} bounce {bouncelist} {bounceend:9.2f} time {timenow:9.2f} ",end='')
                #print(f'    first: {standing}   standlist: {standlist}   bouncelist: {bouncelist}   ',end="")
                #print(f"bounceend {bounceend:9.2f}  ",end="")
                #print(f" timenow {timenow:9.2f}  ",end="")

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
                            keyindex=j
                            playernum=keyindex+1
                            player=players[playernum]
                            # toggle seat enable/disable
                            if player['enable']:
                                player['enable']=False
                            else:
                                player['enable']=True
                            print(f"  player {playernum} enable {player['enable']}  ")
                            standing=chkstand(player['sit'],standlist,player)
                        else: # j<2*max:  # shift 1-9,0 (punctuation) - toggle seat value
                            keyindex=j-max
                            playernum=keyindex+1
                            player=players[playernum]
                            # toggle seat value - for testing
                            if player['sit']:
                                player['sit']=False
                            else:
                                player['sit']=True
                            print(f"  player {playernum}  kdb toggle sit {player['sit']}  ")
                            standing=chkstand(player['sit'],standlist,player)
                        state=player['sit']
                        notbeep=updplayer(state,timenow,notbeep,player,bouncelist)
                    elif c==" ": # space = reset
                        for j in range(max):
                            playernum=j+1
                            players[playernum]['sit']=True
                            players[playernum]['sitnew']=True
                        standlist=[]
                        standing=-1
                        bouncelist=[]
                        bounceend=0
                        print("  reset")
                    elif c=="\n": # enter = show status of each player
                        '''enter is go button'''
                        # debug - show player data
                        print('')
                        for j in range(max):
                            playernum=j+1
                            player=players[playernum]
                            print(player)
                    # can add more keyboard functions above this line
                    else:
                        print(f" char not found:{c}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
'''
quiz controller, text version
'''

import time

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

def main():
    '''quiz-controller-text'''
    # setup
    keys="1234567890!@#$%^&*() \n<>,."
    max=10 # update keys above if this changes
    player=[]   # list of player status
    enable=[]   # enable status of player
    for i in range(max):
        print("player",i,"is key",keys[i])
        player.append(0)
        enable.append(True)

    # test
    player[3]=1

    # main loop
    with NonBlockingConsole() as nbc:
        while True:
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
            time.sleep(.1)






if __name__ == "__main__":
    main()

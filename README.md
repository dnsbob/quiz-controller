
git clone ...
cd ...
python -m venv venv
activate
pip install -r requirements.txt

activate
./quiz-controller-text.py


-~~~
-# quiz-controller
-quiz controller for AWANA Bible drill
 
-To start, use simple text output, black and white, in a terminal.
-mvp (minimum viable product)
 
-Things in [] are future enhancements
-
-Keys:
-testing:
-shift 1-5 and 6-0 - team seat switches, toggle value
-control:
-1-5 and 6-0 - toggle enable/disable seats
-space bar - reset [also start auto reset?]
-enter - ‘go’ button, [ends auto reset]
-<> or “,.” - cycle thru 1st, 2nd, 3rd, etc
-
-Display:
-1st place
-1-5 and 6-0 current state
-[Nth place on each?]
-[time since ‘go’?]
-
-80 col/10 players = 8 spaces each
-[Could do 5x3 or 7x5 big numbers, or just use big text]
-[Colors later]
-
-[Display on projectors?]
-~~~

fanfare is from https://pixabay.com/sound-effects/search/tada/

version 4 has debounce working and fanfare for ready  2025-04-26  rharold

2025-04-30 AWANA Bible drill
When players change seats, need to not beep.
After first player stands, need to not beep for second player, it interrupts the first one reading.
If players are not sitting right on pad, and it toggles when they move but stay seated, the beep is not useful.
Ended up turning off sound.
- Could try to limit sounds, or at least have option to turn off.
- Would help to log the data from the controller to a file for replay later to test with real data.
- Perhaps option to get input from a separate program, which could replay saved data?
- Add option to reduce the display when bouncing, only display when bouce starts and ends
- Log of the output might also be useful
- Try adding a slight delay on the beep for the first player, to detect players not sitting well?
- Add option to simplify display line even more.

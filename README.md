# K6GTE Field Day logger (GUI)

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)  [![Python: 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)  [![Made With:PyQt5](https://img.shields.io/badge/Made%20with-PyQt5-red)](https://pypi.org/project/PyQt5/)

[ARRL Field Day](http://field-day.arrl.org/) is a once a year 24hr emergency preparidness event for radio amateurs (Hams). During the event, we try and make as many radio contacts with other Hams in a 24 hour period. You can find out more about amateur radio by visiting the [ARRL](https://www.arrl.org/).

The logger is written in Python 3, and uses the PyQT5 lib. Qt5 is cross platform so it might work on everything. I have tested it on Linux, Rasperry Pi OS and Windows 10. This code is based off of a logger I had done earlier using Python and the curses library wich can be found [here](https://github.com/mbridak/FieldDayLogger-Curses) and one written for Winter Field Day [here](https://github.com/mbridak/wfd_py_logger).

The log is stored in an sqlite3 database file 'FieldDay.db'. If you need to wipe everything and start clean, just delete this file and re-run the logger

The logger will generate a cabrillo file 'YOURCALL.log' and a 'Statistics.txt' file with a band/mode/power breakdown which you can use when you submit your logs to the ARRL online [here](http://field-day.arrl.org/fdentry.php). An ADIF file will also be generated so you can merge contacts into your normal Log.

![Alt text](https://github.com/mbridak/FieldDayLogger/raw/main/pics/loggerscreenshot.png)

## Experimental feature

I've added a UDP server on port 2333 to accept connections from GridTracker.
If you enable the N1MM+ connection in GridTracker, in theory this Field Day logger should accept the connection as if it was N1MM+ and log the FT8 contact.

Will it work? Mmmmmm sure... Sure it will. I can't really test it untill the day of the event. Sooo Yeah...

Right now it's just active in the sources. I'll try and build the binaries soon.

## Caveats

This is a simple logger ment for single op, it's not usable for clubs.
Field Day only has a generic digital mode designator 'DI', which gets exported to the cabrillo file. But ADIF and CloudLog needed something else, So I Chose FT8. Yes Yes, I know. FT8 is the spawn of Satan, and is killing Ham Radio... Blah Blah Blah... But I needed it for the experiment mentioned above. Flames will be directed to the /dev/null dept. Feel free to change it to what ever you will use. Just search for the two places in the code 'FT8' is used and Bob's your dads brother.

## Running the binary

In the dist directory is the latest binary for Linux [fielddaylogger](https://github.com/mbridak/FieldDayLogger/raw/main/dist/fielddaylogger), Raspberry Pi [fielddaylogger_pi](https://github.com/mbridak/FieldDayLogger/raw/main/dist/fielddaylogger_pi) and Windows 10 [fielddaylogger.exe](https://github.com/mbridak/FieldDayLogger/raw/main/dist/fielddaylogger.exe). You can copy it to a folder in your Linux PATH `/usr/local/bin` or `~/bin` or on either platform just run it where ever it happens to be. Or you can follow the steps below to run it from source.

## Installing an icon

If you wish you can install a Linux desktop/menu icon launcher by going to the install_icon folder and running the `install.sh` script. and to remove the hideous icon later, run the `uninstall.sh` script

## Running from source

Install Python 3, then two required libs via pip.

`pip install PyQt5`

and

`pip install requests`

or you may have to type:

`python3 -m pip install PyQt5`

and

`python3 -m pip install requests`

Just make fielddaylogger.py executable and run it within the same folder, or type:

`python3 fielddaylogger.py`

## What to do first

When run for the first time, you will need to set your callsign, class, section, band, mode and power used for the contacts. This can be found at the bottom of the screen.

![Alt text](https://github.com/mbridak/FieldDayLogger/raw/main/pics/yourstuff.png)

## Logging

Okay you've made a contact. Enter the call in the call field. As you type it in, it will do a super check partial (see below). Press TAB or SPACE to advance to the next field. Once the call is complete it will do a DUP check (see below).
 It will try and Autofill the next fields (see below). When entering the section, it will do a section partial check (see below). Press the ENTER key to submit the Q to the log. If it's a busted call or a dup, press the ESC key to clear all inputs and start again.

# Features

## Radio Polling via rigctld

If you run rigctld on a computer connected to the radio, it can be polled for band/mode updates automatically. Click the gear icon at the bottom of the screen to set the IP and port for rigctld. There is a radio icon at the bottom of the logging window to indicate polling status.

![Alt text](https://github.com/mbridak/FieldDayLogger/raw/main/pics/loggerSettingsDialog.png)

## Cloudlog, QRZ, HamDB useage

If you use either Cloudlog logging or QRZ/HamDB lookup you can click the gear icon to enter your credentials. Q's are pushed to CloudLog as soon as they are logged.

The QRZ/HamDB lookup is only used to get the name and gridsquare for the call. Mainly because when a Q is pushed to [CloudLog](https://github.com/magicbug/Cloudlog) it will not show as a pin on the map unless it has a gridsquare. So this is a scratch my own itch feature. Just place a check in either box to use them. If both are checked it will it will use QRZ.
If you have no internet connection leave these unchecked since it might cause a delayafter entering your Q.

## XPlanet marker file

If you use QRZ/HamdDB lookups you can also generate an [XPlanet](http://xplanet.sourceforge.net/) markerfile which will show little pips on the map as contacts are logged.

![Alt text](https://github.com/mbridak/FieldDayLogger/raw/main/pics/xplanet.png)

The above launched with an example command:

```bash
xplanet -body earth -window -longitude -117 -latitude 38 -config Default -projection azmithal -radius 200 -wait 5
```

## Editing an existing contact

Double click a contact in the upper portion of the screen to edit or delete it.

![Alt text](https://github.com/mbridak/FieldDayLogger/raw/main/pics/editqso.png)

## Super Check Partial

If you type more than two characters in the callsign field the program will filter the input through a "Super Check Partial" routine and show you possible matches to known contesting call signs. Is this useful? Doubt it.

![Alt text](https://github.com/mbridak/FieldDayLogger/raw/main/pics/scp.png)

## Section partial check

As you type the section abbreviation you are presented with a list of all possible sections that start with what you have typed.

![Alt text](https://github.com/mbridak/FieldDayLogger/raw/main/pics/sectioncheck.png)

## DUP checking

Once you type a complete callsign and press TAB or SPACE to advance to the next field. The callsign is checked against previous callsigns in your log. It will list any prior contact made showing the band and mode of the contact. If the band and mode are the same as the one you are currently using, the listing will be highlighted, the screen will flash, a bell will sound to alert you that this is a DUP. At this point you and the other OP can argue back and forth about who's wrong. In the end you'll put your big boy pants on and make a decision if you'll enter the call or not.

![Alt text](https://github.com/mbridak/FieldDayLogger/raw/main/pics/dupe.png)

## Autofill

If you have worked this person before on another band/mode the program will load the class and section used previously for this call so you will not have to enter this info again.

## When the event is over

After the big weekend, once you've swept up all the broken beer bottles and wiped the BBQ sauce off your chin, go ahead and click the Generate Logs button.

![Alt text](https://github.com/mbridak/FieldDayLogger/raw/main/pics/genlog.png)

This will generate the following:

An ADIF log 'FieldDay.adi'.

A Cabrillo log 'Yourcall.log'. Which you edit to fill in your address etc. If your not using Windows, you must ensure whatever editor you use uses CR/LF line endings. Cause whatever they use at the ARRL will choke with out them. To be safe you might want to run it through 'unix2dos' before submitting it.

A 'Statistics.txt' file which breaks down your band/mode/power usage.

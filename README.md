# K6GTE Field Day logger (GUI)

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)  [![Python: 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)  [![Made With:PyQt5](https://img.shields.io/badge/Made%20with-PyQt5-red)](https://pypi.org/project/PyQt5/)
![PyPI - Downloads](https://img.shields.io/pypi/dm/fdlogger)

[ARRL Field Day](http://field-day.arrl.org/) is a once a year 24hr emergency
preparidness event for radio amateurs (Hams). During the event, we try and
make as many radio contacts with other Hams in a 24 hour period. You can find
out more about amateur radio by visiting the [ARRL](https://www.arrl.org/).

The logger is written in Python 3, and uses the PyQT5 lib. Qt5 is cross
platform so it might work on everything. I have tested it on Linux, Rasperry
Pi OS and Windows 10. This code is based off of a logger I had done earlier
using Python and the curses library wich can be found
[here](https://github.com/mbridak/FieldDayLogger-Curses) and one written for
Winter Field Day [here](https://github.com/mbridak/wfd_py_logger).

The log is stored in an sqlite3 database file 'FieldDay.db'. If you need to
wipe everything and start clean, just delete this file and re-run the logger

The logger will generate a cabrillo file 'YOURCALL.log' and a 'Statistics.txt'
file with a band/mode/power breakdown which you can use when you submit your
logs to the ARRL online [here](http://field-day.arrl.org/fdentry.php). An ADIF
file will also be generated so you can merge contacts into your normal Log.

We now have a group aggregation server, The clients and server pass traffic
over Multicast UDP.

- [K6GTE Field Day logger (GUI)](#k6gte-field-day-logger-gui)
  - [Caveats](#caveats)
  - [Recent Changes](#recent-changes)
  - [Wheres the data](#wheres-the-data)
  - [Installation and running and removal](#installation-and-running-and-removal)
  - [What to do first](#what-to-do-first)
- [Features](#features)
  - [Logging](#logging)
  - [Radio Polling with CAT](#radio-polling-with-cat)
    - [Without CAT](#without-cat)
  - [Cloudlog useage](#cloudlog-useage)
  - [QRZ, HamDB or HamQTH](#qrz-hamdb-or-hamqth)
  - [XPlanet marker file](#xplanet-marker-file)
  - [Editing an existing contact](#editing-an-existing-contact)
  - [Super Check Partial](#super-check-partial)
  - [Section partial check](#section-partial-check)
  - [DUP checking](#dup-checking)
  - [Autofill](#autofill)
  - [CW Macros](#cw-macros)
  - [CW Macros (Run vs S\&P)](#cw-macros-run-vs-sp)
  - [CWDAEMON speed changes](#cwdaemon-speed-changes)
  - [When the event is over](#when-the-event-is-over)
  - [Group / Club logging](#group--club-logging)
    - [Server configuration](#server-configuration)
    - [Client configuration for groups](#client-configuration-for-groups)
    - [Chat Window](#chat-window)
    - [How to know the server is there](#how-to-know-the-server-is-there)
    - [Logging reliability](#logging-reliability)
    - [Generating the cabrillo file](#generating-the-cabrillo-file)
    - [I'm sure there are short cummings](#im-sure-there-are-short-cummings)

![Picture of main screen](https://github.com/mbridak/FieldDayLogger/raw/main/pics/loggerscreenshot.png)

![Picture of server main screen](https://github.com/mbridak/FieldDayLogger/raw/main/pics/server_pic.png)

## Caveats

This has always been a "scratch my own itch" project. And the development of
it is driven by that. However, I welcome suggestions, criticisms and feature
requests.

Field Day only has a generic digital mode designator 'DG', which gets exported
to the cabrillo file. But ADIF and CloudLog needed something else, So I Chose
FT8. Yes Yes, I know. FT8 is the spawn of Satan, and is killing Ham Radio...
Blah Blah Blah... Feel free to change it to what ever you will use.
Just search for the two places in the code 'FT8' is used and Bob's your dads
brother.

**WB8ERJ's blog writeup** [Mike's Tech Blog WB8ERJ](https://mikestechblog.com/field-day-logging-software-for-the-raspberry-pi/)

## Recent Changes

- [24.2.21] Added OPON.
- [24.2.19] Corrected the datetime.utcnow() deprecation to work on Python 3.9+
- [24.2.11] Trapped a KeyError in get_state()
- [24.1.27] Removed some datetime.utcnow() and pkgutil.getloader() deprecations.
- [23.11.9] Merged from @wvolz fixing crash related to tuning to a non ham band.
- [23.6.25] Fixed missing Canadian sections.
- [23.6.24] Fix 6M CW default frequency. Wierdness with VFO fixed.
- [23.6.23] Entering freq in Khz in the callsign field sets the VFO.
- [23.6.22] Fix postcloudlog, Value unpack count mismatch.
- [23.6.21] Fixed xplanet marker file. I think.
- [23.6.18] Small visual change to interface.
- [23.6.12] Merged PR from @wvolz to handle MacOS port reuse.
- [23.6.9] Added server dupe check. Thanks @kybrjo, Be sure to pip update the fdserver for this. Bugfix: was unable to edit frequency. Thanks @km4ack.
- [23.5.31] Replaced some deleted stuff. Thanks @ATCUSA for finding it!
- [23.5.30] Changed default multicast address from 224.1.1.1 to 239.1.1.1
- [23.4.8] Fixed crash on setting setup.
- [23.2.3] Fixed crash when qrz or hamqth was used. Fixed crash when not debugging. Contact lookup now shows in infoline. Reduced font size in the group chat window. Improved debug logging.
- [23.2.2] Added N1MM status packets. fdserver program moved into it's own repo/PyPi package.
- [23.2.1] Made interface resizable.
- [23.1.30] Repackaged for PyPi pip installation

## Wheres the data

The client log is stored in an sqlite3 database file './FieldDay.db'. If you
need to wipe everything and start clean, just delete this file and re-run the
logger.

The aggrigation server stores it's database in a file called, in a stroke of
inspiration, './server_database.db'.

The logger will generate a cabrillo file './YOURCALL.log' and a
'./Statistics.txt' file with a band/mode/power breakdown which you can use
when you submit your logs to the ARRL online
[here](http://field-day.arrl.org/fdentry.php).

The server will generate a cabrillo file './YOURCLUBSCALLSIGN.log'

An ADIF file './FieldDay.adi' will also be generated by the client so you can
merge contacts into your normal Log.

The server does not create an adif file, 'cause why should it...

## Installation and running and removal

```bash
# install
pip install fdlogger

# update
pip install -U fdlogger

# remove
pip uninstall fdlogger

# run it
fdlogger
```

If you get a message about `./local/bin` not being in your PATH, try logging out and right back in. Most of the time your linux distro will detect you now have files in there and add it to your PATH.

## What to do first

When run for the first time, you will be greeted by a dialog asking for your
Callsign, Class and Section. Afterward, there is a gear icon on the main
screen, where you can change your CAT, CW interface, callsign lookup service
etc. You can also change your call class and section by clicking on the
respective fields.

![Picture showing bottom of screen](https://github.com/mbridak/FieldDayLogger/raw/main/pics/yourstuff.png)

![Picture showing settings screen](https://github.com/mbridak/FieldDayLogger/raw/main/pics/loggerSettingsDialog.png)

# Features

## Logging

Okay you've made a contact. Enter the call in the call field. As you type it
in, it will do a super check partial (see below). Press TAB or SPACE to
advance to the next field. Once the call is entered and you've moved to the
next field, it will do a DUP check (see below). It will try and Autofill the
next fields (see below). When entering the section, it will do a section
partial check (see below). Press the ENTER key to submit the contact to the
log.

If it's a busted call or a dup, press the ESC key to clear all inputs and
start again.

## Radio Polling with CAT

If you run flrig or rigctld on a computer connected to the radio, it can be
polled for band/mode updates automatically. Click the gear icon at the bottom
of the screen to set the IP and port and choose flrig or rigctld. The default
ports are 4532 for rigctld and 12345 for flrig.  There is a radio icon at the
bottom of the logging window to indicate polling status. Green good, Red bad.

### Without CAT

If your radio does not provide CAT control, The frequency can be specified by
entering the frequency in the callsign field in kilohertz, then pressing the
spacebar. So a 20M CW contact might be entered as 14032.5

If you do not enter a frequency, a sane value is chosen for you. This is fine.
Since a specific frequency is not required for Field Day.

## Cloudlog useage

If you use [CloudLog](https://github.com/magicbug/Cloudlog) for your main
logging you can click the gear icon to enter your credentials. Contacts are
pushed to CloudLog as soon as they are logged.

## QRZ, HamDB or HamQTH

The QRZ/HamDB/HamQTH lookup is only used to get the name and gridsquare for
the call. Mainly because when a contact is pushed to
[CloudLog](https://github.com/magicbug/Cloudlog) it will not show as a pin on
the map unless it has a gridsquare. So this is a scratch my own itch feature.

The call to the lookup service is made anytime you exit the call entry field
by pressing a TAB or Space key. This call is done in it's own thread so it will
not slow down the GUI interface.

Distance and bearing to contact is also calculated at this time, though I
haven't made use of the data.

## XPlanet marker file

If you use QRZ/HamdDB lookups you can also generate an
[XPlanet](http://xplanet.sourceforge.net/) markerfile which will show little
pips on the map as contacts are logged.

![Picture showing xplanet](https://github.com/mbridak/FieldDayLogger/raw/main/pics/xplanet.png)

The above launched with an example command:

```bash
xplanet -body earth -window -longitude -117 -latitude 38 -config Default -projection azmithal -radius 200 -wait 5
```

## Editing an existing contact

Double click a contact in the upper portion of the screen to edit or delete it.

![Picture showing edit qso dialog](https://github.com/mbridak/FieldDayLogger/raw/main/pics/editqso.png)

## Super Check Partial

If you type more than two characters in the callsign field the program will
filter the input through a "Super Check Partial" routine and show you possible
matches to known contesting call signs. Is this useful? Doubt it.

![Picture showing super check partial](https://github.com/mbridak/FieldDayLogger/raw/main/pics/scp.png)

## Section partial check

As you type the section abbreviation you are presented with a list of all
possible sections that start with what you have typed.

![Picture showing section check partial](https://github.com/mbridak/FieldDayLogger/raw/main/pics/sectioncheck.png)

## DUP checking

Once you type a complete callsign and press TAB or SPACE to advance to the next
field. The callsign is checked against previous callsigns in your log. It will
list any prior contact made showing the band and mode of the contact. If the
band and mode are the same as the one you are currently using, the listing will
be highlighted, the screen will flash, a bell will sound to alert you that this
is a DUP. At this point you and the other OP can argue back and forth about
who's wrong. In the end you'll put your big boy pants on and make a decision if
you'll enter the call or not.

![Picture showing dup checking](https://github.com/mbridak/FieldDayLogger/raw/main/pics/dupe.png)

If you are using the group server, the client will poll the server as well asking if this is a dupe.

## Autofill

If you have worked this person before on another band/mode the program will
load the class and section used previously for this call so you will not have
to enter this info again.

## CW Macros

The program will check in the current working directory for a file called
`cwmacros_fd.txt`. If not present it will be created. It will parse the file
and configure the row of 12 buttons along the bottom half of the window.
The macros can be activated by either pressing the corresponding function key,
or by directly clicking on the button. You can check the file to glean it's
structure, but it's pretty straight forward. Each line has 4 sections separated
by the pipe `|` character.
Here's an example line.

`R|F2|Run Exch|{HISCALL} {MYCLASS} {MYSECT}`

The first field is an `R` if the macro is to be shown while in Run mode.
Otherwise an `S` for Search and Pounce. The second field is the function key
to program. The third is the text label to put in the button. Lastly the
fourth is the text you would like to send.

A limited set of substitution macros are offered.

`{MYCALL}`
`{HISCALL}`
`{MYCLASS}`
`{MYSECT}`

These are pulled straight from the onscreen input fields. Combined with normal
text this should have you covered for most of your exchange needs.

## CW Macros (Run vs S&P)

You can toggle the macros in use between Run and Search and Pounce by clicking
the button to the left of the settings/gear button at the botton right portion
of the screen.

![Picture showing buttons](https://github.com/mbridak/FieldDayLogger/raw/main/pics/run_sp.png)

This can also be used to reload the macros if you edit them while the program
is running.

## CWDAEMON speed changes

If you use cwdaemon for your cw macro sending, you can press the PageUp and
PageDown keys on your keyboard to increase/decrease the cw sending speed.
You can press `ESC` to abort CW output.

## When the event is over

After the big weekend, once you've swept up all the broken beer bottles and
wiped the BBQ sauce off your chin, go ahead and click the Generate Logs button.

![Picture showing generate log button](https://github.com/mbridak/FieldDayLogger/raw/main/pics/genlog.png)

This will generate the following:

An ADIF log 'FieldDay.adi'.

A Cabrillo log 'Yourcall.log'. Which you edit to fill in your address etc.
If your not using Windows, you must ensure whatever editor you use uses CR/LF
line endings. Cause whatever they use at the ARRL will choke with out them.
To be safe you might want to run it through 'unix2dos' before submitting it.

A 'Statistics.txt' file which breaks down your band/mode/power usage.

## Group / Club logging

I have added a group contact aggrigating server. This can be run on the same
computer as the client program, or on a separate dedicated PC or Raspberry Pi
on the same network.

![Picture showing main server screen](https://github.com/mbridak/FieldDayLogger/raw/main/pics/server_pic.png)

### Server configuration

The configuration file for the server is a JSON file 'server_preferences.json'.

```json
{
    "ourcall": "W1AW",
    "ourclass": "3A",
    "oursection": "ORG",
    "bonus": {
        "emergency_power": {
            "bool": 0,
            "station_count": 0
        },
        "media_publicity": 0,
        "public_location": 0,
        "public_info_table": 0,
        "message_to_section_manager": 0,
        "message_handling": {
            "bool": 0,
            "message_count": 0
        },
        "satellite_qso": 0,
        "w1aw_bulletin": 0,
        "educational_activity": 0,
        "elected_official_visit": 0,
        "agency_representative_visit": 0,
        "gota": 0,
        "web_submission": 0,
        "youth_participation": {
            "bool": 0,
            "youth_count": 0
        },
        "social_media": 0,
        "safety_officer": 0
    },
    "batterypower": 1,
    "name": "Hiram Maxim",
    "address": "225 Main Street",
    "city": "Newington",
    "state": "CT",
    "postalcode": "06111",
    "country": "USA",
    "email": "Hiram.Maxim@arrl.net",
    "mullticast_group": "239.1.1.1",
    "multicast_port": 2239,
    "interface_ip": "0.0.0.0",
}
```

Go ahead and edit this file before running the server. Feel free to leave the
last 3 items as they are unless you have good reason not too. The rest should
be straight forward.

Under the bonuses section, if your group qualifies for a bonus, replace the '0'
next to the bonus with a '1'. Three of the bonuses require a count of items
qualifiying you for the bonus. For example Message Handling. If your group
qualifies for this, change the value of 'bool' to a 1, and then 'message_count'
to the number of messages handled.

### Client configuration for groups

In the settings dialog there is now a tab labeled 'Group Operation'.

![Picture showing settings dialog tab](https://github.com/mbridak/FieldDayLogger/raw/main/pics/group_server_settings.png)

Go ahead and place a check next to 'Connect to server'. Rejoyce and let
merriment be had by all. Be sure and have your callsign already set before
checking this. If you forgot, Uncheck it, set your callsign and then check it.

A couple of things will change on the client when this is done. You will see
that your callsign will disappear and be replaced with your clubs call that the
server reports. The portion of the screen where all the different ARRL sections
are displayed will be replaced by a group chat window and a column showing the
station call, band and mode of other participants.

![Picture showing logger screen changes](https://github.com/mbridak/FieldDayLogger/raw/main/pics/group_chat.png)

If more than one operator is on the same band/mode, their names will be
highlighted in the operators list. Feel free to yell at eachother in the chat.

![Picture showing band and mode conflict](https://github.com/mbridak/FieldDayLogger/raw/main/pics/band_conflict.png)

### Chat Window

The chat window is pretty straight forward. If someone mentions you in the chat
that line will be highlighted with an accent color. If you find the font size
does not work for you, can adjust the size by: Placing your mouse cursor in the
chat window, then rotate your mouse wheel while holding down the Control key.

There is one command you can type into the chat window that may be of use.
if you type `@stats` into the window, the server will dump out some stats into the
chat.

```text
Server: 
Band   CW    PH    DI
 160     0     0     0
  80     0     0    25
  40     0   159     0
  20     1   162   126
  15     0     0     0
  10     0     0     0
   6     0    17     0
   2     0     0     0

Score: 1284
Last Hour: 271
Last 15: 81
```

Since most people will not be able to see the screen of the server, if it has
one at all. You may find this useful.

### How to know the server is there

Most likely, the server will be in some other tent/building/area of the room.
Every 10 seconds or so the server will send out a UDP network packet saying
it's there. As long as your client keeps seeing these packets the group call
indicator at the bottom of the screen will look like:

![Picture showing server status](https://github.com/mbridak/FieldDayLogger/raw/main/pics/server_pinging.png)

But if about 30 seconds go by with no update from the server, the indicator
will change to:

![Picture showing server status](https://github.com/mbridak/FieldDayLogger/raw/main/pics/server_not_pinging.png)

Go check on it.

### Logging reliability

As mentioned before, We're using UDP traffic to pass data back and forth to the
server. UDP traffic is a 'Fire and forget' method. Akin to a bunch of people
in the same room yelling at eachother. Everyone can hear you, but you don't
know if anyone heard what you said. This has both Advantages and Disadvantages.
One advantage is that your program is not stuck waiting for a reply or timeout
locking up your user interface. The disadvantage is you have no idea if anyone
took note of what you had said.

This works fine in a local network since the traffic doesn't have to survive
the trip through the big bad tubes of the internet. That being said, someone
may trip on a cord, unplugging the router/switch/wireless gateway. Or someone
may be trying to use WIFI and they are Soooooo far away you can barely see
their tent. Or worse you have EVERYONE on WIFI, and there are packet collisions
galore degrading your network.

To account for this, the client logging program keeps track of recent packets
sent, noting the time they were sent at. The server after getting a packet,
generates a response to the sender with it's unique identifyer. Once the client
gets the response from the server, it will remove the request on the local side
and print a little message at the bottom of the screen giving you a visual
confirmation that the command was acted upon by the server.
If the server does not respond either because the response was lost or the
request never made it to reply too. The client will resend the
packet every 30 seconds until it gets a reply.

But all this may still result in the server not having a copy of your contact.
To account for this, when the "Generate Logs" button is pressed on the client,
the client will resend all the logged contacts that have not gotten responses
from the server. You can keep doing this, if need be,  until it gets them all.

Chat traffic is best effort. Either everyone sees your plea for more beer or
they don't. No retry is made for chat traffic. Just get your butt up and make
the trip to the cooler.

### Generating the cabrillo file

If any of the networked clients presses the 'Generate Logs' button on their
screen, the server will be told to generate it's cabrillo file, it will be
named 'WhatEverYourClubCallIs.log'

### I'm sure there are short cummings

It's early days, and I've mainly tested the operations with the client logging
program and several simulated operators, see file in `testing/simulant.py`
Real world use for Field Day in September is hard to come by. So I'm sure there
are a couple of things I forgot, or didn't account for.

If you are part of a group of linux using Hams, please take this for a spin and
tell me what I missed or could do better.

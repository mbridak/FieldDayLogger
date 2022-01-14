#! /usr/bin/env python3

"""
This is an RBN spot bandmap list which filters the spotters by distance.
If you limit the RBN spotting stations to those closest to you, you can
limit the reported spots to those you can actually have a chance to hear.
It does no good to get WFD CW spots from Italy if you're in Texas...

Change the 'mygrid' variable to your own grid.
Change the 'maxspotterdistance' to some distance in miles.

I'm in SoCal so I set mine to 500 wich gets me about 8 regional spotters.
If your in South Dakota, you may have to expand your circle a bit.

An easy way to start, is check the RBN when you call CQ to see who spots You.
Find the furthest spotter, figure out how far away they are and make that your distance.

The 'showoutofband' variable if True, will show spots outside of the General band. If your an
Advanced or Extra make sure this is true. If you're a general like me, make it false.
No use in seeing spots you can respond to...
"""

import logging
from rich.logging import RichHandler

logging.basicConfig(
    level="CRITICAL",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)
from rich.traceback import install

install(show_locals=True)

import xmlrpc.client
import requests
import sqlite3
import re
import time
import argparse

from threading import Thread, Lock
from sqlite3 import Error
from telnetlib import Telnet
from rich.console import Console
from rich import print
from bs4 import BeautifulSoup as bs
from math import radians, sin, cos, atan2, sqrt

parser = argparse.ArgumentParser(
    description="Pull RBN spots, filter spotters w/ in a certain distance."
)
parser.add_argument("-c", "--call", type=str, help="Your callsign")
parser.add_argument("-m", "--mygrid", type=str, help="Your gridsquare")
parser.add_argument(
    "-d",
    "--distance",
    type=int,
    help="Limit to radius in miles from you to spotter, default is: 500",
)
parser.add_argument(
    "-g",
    "--general",
    action="store_true",
    help="Limit spots to general portion of the band.",
)
parser.add_argument(
    "-a", "--age", type=int, help="Drop spots older than (age) seconds. Default is: 600"
)
parser.add_argument(
    "-r", "--rbn", type=str, help="RBN server. Default is: telnet.reversebeacon.net"
)
parser.add_argument(
    "-p", "--rbnport", type=int, help="RBN server port. Default is: 7000"
)
parser.add_argument(
    "-b",
    "--bands",
    nargs="+",
    type=int,
    help="Space separated list of bands to receive spots about. Default is: 160 80 40 20 15 10 6",
)
parser.add_argument(
    "-f", "--flrighost", type=str, help="Hostname/IP of flrig. Default is: localhost"
)
parser.add_argument("-P", "--flrigport", type=int, help="flrig port. Default is: 12345")
parser.add_argument(
    "-l", "--log", type=str, help="Log DB file to monitor. Default is: FieldDay.db"
)

args = parser.parse_args()

if args.call:
    mycall = args.call
else:
    mycall = "w1aw"

if args.mygrid:
    mygrid = args.mygrid.upper()
else:
    mygrid = "DM13AT"

if args.distance:
    maxspotterdistance = args.distance
else:
    maxspotterdistance = 500

if args.general:
    showoutofband = False
else:
    showoutofband = True

if args.age:
    spottoold = args.age
else:
    spottoold = 600  # 10 minutes

if args.rbn:
    rbn = args.rbn
else:
    rbn = "telnet.reversebeacon.net"

if args.rbnport:
    rbnport = args.rbnport
else:
    rbnport = 7000

if args.bands:
    limitband = tuple(map(str, args.bands))
else:
    limitband = ("160", "80", "40", "20", "15", "10", "6")

if args.flrighost:
    flrighost = args.flrighost
else:
    flrighost = "localhost"

if args.flrigport:
    flrigport = args.flrigport
else:
    flrigport = 12345

if args.log:
    logdb = args.log
else:
    logdb = "FieldDay.db"

server = xmlrpc.client.ServerProxy(f"http://{flrighost}:{flrigport}")
conn = False
lock = Lock()
console = Console(width=38)
localspotters = list()
vfo = 0.0
oldvfo = 0.0
contactlist = dict()
rbn_parse = r"^DX de ([A-Z\d\-\/]*)-#:\s+([\d.]*)\s+([A-Z\d\-\/]*)\s+([A-Z\d]*)\s+(\d*) dB.*\s+(\d{4}Z)"


def updatecontactlist():
    """
    Scans the loggers database and builds a callsign on band dictionary
    so the spots can be flagged red so you know you can bypass them on the bandmap.
    """
    global contactlist
    contactlist = dict()
    try:
        with sqlite3.connect(logdb) as conn:
            c = conn.cursor()
            sql = "SELECT COUNT(*) as hascolumn FROM pragma_table_info('contacts') WHERE name='mode';"
            c.execute(sql)
            hascolumn = c.fetchone()[0]
            if hascolumn:
                sql = "select * from contacts where mode='CW'"
            else:
                sql = "select * from contacts"
            c.execute(sql)
            result = c.fetchall()
            for contact in result:
                if hascolumn:
                    _, callsign, _, _, _, band, _, _, _, _ = contact
                else:
                    _, callsign, _, _, _, _, band, _, _ = contact
                if band in contactlist.keys():
                    contactlist[band].append(callsign)
                else:
                    contactlist[band] = list()
                    contactlist[band].append(callsign)
    except Error as e:
        console.print(e)


def alreadyworked(callsign, band):
    """
    Check if callsign has already been worked on band.
    """
    global contactlist
    if str(band) in contactlist:
        return callsign in contactlist[str(band)]
    return False


def getvfo():
    """
    Get the freq from the active VFO in khz.
    """
    global vfo
    while True:
        try:
            vfo = float(server.rig.get_vfo()) / 1000
        except:
            vfo = 0.0
        time.sleep(0.25)


def comparevfo(freq):
    """
    Return the difference in khz between the VFO and the spot.
    Spots show up in Blue, Grey, Dark Grey, Black backgrounds depending on how far away you VFO is.
    """
    global vfo
    freq = float(freq)
    difference = 0.0
    if vfo < freq:
        difference = freq - vfo
    else:
        difference = vfo - freq
    return difference


def gridtolatlon(maiden):
    """
    Convert a 2,4,6 or 8 character maidenhead gridsquare to a latitude longitude pair.
    """
    maiden = str(maiden).strip().upper()

    N = len(maiden)
    if not 8 >= N >= 2 and N % 2 == 0:
        return 0, 0

    lon = (ord(maiden[0]) - 65) * 20 - 180
    lat = (ord(maiden[1]) - 65) * 10 - 90

    if N >= 4:
        lon += (ord(maiden[2]) - 48) * 2
        lat += ord(maiden[3]) - 48

    if N >= 6:
        lon += (ord(maiden[4]) - 65) / 12 + 1 / 24
        lat += (ord(maiden[5]) - 65) / 24 + 1 / 48

    if N >= 8:
        lon += (ord(maiden[6])) * 5.0 / 600
        lat += (ord(maiden[7])) * 2.5 / 600

    return lat, lon


def getband(freq):
    """
    Convert a (float) frequency into a (string) band.
    Returns a (string) band.
    Returns a "0" if frequency is out of band.
    """
    try:
        frequency = int(float(freq)) * 1000
    except:
        frequency = 0.0
    if frequency > 1800000 and frequency < 2000000:
        return "160"
    if frequency > 3500000 and frequency < 4000000:
        return "80"
    if frequency > 5330000 and frequency < 5406000:
        return "60"
    if frequency > 7000000 and frequency < 7300000:
        return "40"
    if frequency > 10100000 and frequency < 10150000:
        return "30"
    if frequency > 14000000 and frequency < 14350000:
        return "20"
    if frequency > 18068000 and frequency < 18168000:
        return "17"
    if frequency > 21000000 and frequency < 21450000:
        return "15"
    if frequency > 24890000 and frequency < 24990000:
        return "12"
    if frequency > 28000000 and frequency < 29700000:
        return "10"
    if frequency > 50000000 and frequency < 54000000:
        return "6"
    if frequency > 144000000 and frequency < 148000000:
        return "2"

    return "0"


def calc_distance(grid1, grid2):
    """
    Takes two maidenhead gridsquares and returns the distance between the two in kilometers.
    """
    R = 6371  # earh radius
    lat1, long1 = gridtolatlon(grid1)
    lat2, long2 = gridtolatlon(grid2)

    d_lat = radians(lat2) - radians(lat1)
    d_long = radians(long2) - radians(long1)

    r_lat1 = radians(lat1)
    r_long1 = radians(long1)
    r_lat2 = radians(lat2)
    r_long2 = radians(long2)

    a = sin(d_lat / 2) * sin(d_lat / 2) + cos(r_lat1) * cos(r_lat2) * sin(
        d_long / 2
    ) * sin(d_long / 2)
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    d = R * c  # distance in km

    return d


def inband(freq):
    """
    Returns True if the frequency is within the General portion of the band.
    """
    ib = False
    if freq > 1800 and freq < 2000:
        ib = True
    if freq > 3525 and freq < 3600:
        ib = True
    if freq > 3800 and freq < 4000:
        ib = True
    if freq > 7025 and freq < 7125:
        ib = True
    if freq > 7175 and freq < 7300:
        ib = True
    if freq > 10100 and freq < 10150:
        ib = True
    if freq > 14025 and freq < 14150:
        ib = True
    if freq > 14225 and freq < 14350:
        ib = True
    if freq > 18068 and freq < 18168:
        ib = True
    if freq > 21025 and freq < 21200:
        ib = True
    if freq > 21275 and freq < 21450:
        ib = True
    if freq > 24890 and freq < 24990:
        ib = True
    if freq > 28000 and freq < 29700:
        ib = True
    if freq > 50000 and freq < 54000:
        ib = True
    return ib


def addSpot(callsign, freq, band):
    """
    Removes spots older than value stored in spottoold.
    Inserts a new or updates existing spot.
    """
    global spottoold
    with sqlite3.connect("spots.db") as conn:
        spot = (callsign, freq, band)
        c = conn.cursor()
        sql = f"delete from spots where Cast ((JulianDay(datetime('now')) - JulianDay(date_time)) * 24 * 60 * 60 As Integer) > {spottoold}"
        c.execute(sql)
        conn.commit()
        sql = f"select count(*) from spots where callsign='{callsign}'"
        c.execute(sql)
        result = c.fetchall()
        if result[0][0] == 0:
            sql = "INSERT INTO spots(callsign, date_time, frequency, band) VALUES(?,datetime('now'),?,?)"
            c.execute(sql, spot)
            conn.commit()
        else:
            sql = f"update spots set frequency='{freq}', date_time = datetime('now'), band='{band}' where callsign='{callsign}';"
            c.execute(sql)
            conn.commit()


def pruneoldest():
    """
    Removes the oldest spot.
    """
    with sqlite3.connect("spots.db") as conn:
        c = conn.cursor()
        sql = "select * from spots order by date_time asc"
        c.execute(sql)
        result = c.fetchone()
        id, _, _, _, _ = result
        sql = f"delete from spots where id='{id}'"
        c.execute(sql)
        conn.commit()


def showspots(lock):
    """
    Show spot list, sorted by frequency.
    Prune the list if it's longer than the window by removing the oldest spots.
    If tracking your VFO highlight those spots in/near your bandpass.
    Mark those already worked in red.
    """
    global vfo
    while True:
        updatecontactlist()
        console.clear()
        console.rule(f"[bold red]Spots VFO: {vfo}")
        with lock:
            with sqlite3.connect("spots.db") as conn:
                c = conn.cursor()
                sql = "select *, Cast ((JulianDay(datetime('now')) - JulianDay(date_time)) * 24 * 60 * 60 As Integer) from spots order by frequency asc"
                c.execute(sql)
                result = c.fetchall()
        displayed = 2
        for x, spot in enumerate(result):
            _, callsign, date_time, frequency, band, delta = spot
            displayed += 1
            if displayed > console.height:
                with lock:
                    pruneoldest()
            else:
                if inband(frequency):
                    style = ""
                else:
                    style = ""  # if in extra/advanced band
                if comparevfo(frequency) < 0.8:
                    style = "bold on color(237)"
                if comparevfo(frequency) < 0.5:
                    style = "bold on color(240)"
                if comparevfo(frequency) < 0.2:
                    style = "bold on blue"
                if alreadyworked(callsign, band):
                    style = "bold on color(88)"
                console.print(
                    f"{callsign.ljust(11)} {str(frequency).rjust(8)} {str(band).rjust(3)}M {date_time.split()[1]} {delta}",
                    style=style,
                    overflow="ellipsis",
                )
        time.sleep(1)


def getrbn(lock):
    with Telnet(rbn, rbnport) as tn:
        while True:
            stream = tn.read_until(b"\r\n", timeout=1.0)
            if stream == b"":
                continue
            stream = stream.decode()
            if "Please enter your call:" in stream:
                tn.write(f"{mycall}\r\n".encode("ascii"))
                continue
            data = stream.split("\r\n")
            for entry in data:
                if not entry:
                    continue
                parsed = list(re.findall(rbn_parse, entry.strip()))
                if not parsed or len(parsed[0]) < 6:
                    continue
                spotter = parsed[0][0]
                mode = parsed[0][3]
                if not mode == "CW":
                    continue
                if not spotter in localspotters:
                    continue
                freq = float(parsed[0][1])
                band = getband(freq)
                callsign = parsed[0][2]
                if not inband(float(freq)) and showoutofband == False:
                    continue
                if band in limitband:
                    with lock:
                        addSpot(callsign, freq, band)


console.clear()
updatecontactlist()
console.rule("[bold red]Finding Spotters")
page = requests.get(
    "http://reversebeacon.net/cont_includes/status.php?t=skt", timeout=10.0
)
soup = bs(page.text, "lxml")
rows = soup.find_all("tr", {"class": "online"})
for row in rows:
    datum = row.find_all("td")
    spotter = datum[0].a.contents[0].strip()
    bands = datum[1].contents[0].strip()
    grid = datum[2].contents[0]
    distance = calc_distance(grid, mygrid) / 1.609
    if distance < maxspotterdistance:
        localspotters.append(spotter)

print(f"Spotters with in {maxspotterdistance} mi:")
print(f"{localspotters}")
time.sleep(1)
with sqlite3.connect("spots.db") as conn:
    c = conn.cursor()
    sql_table = """CREATE TABLE IF NOT EXISTS spots (id INTEGER PRIMARY KEY, callsign text, date_time text NOT NULL, frequency REAL NOT NULL, band INTEGER);"""
    c.execute(sql_table)
    sql = f"delete from spots where Cast ((JulianDay(datetime('now')) - JulianDay(date_time)) * 24 * 60 * 60 As Integer) > {spottoold}"
    c.execute(sql)
    conn.commit()

# Threading Oh my!
t1 = Thread(target=getrbn, args=(lock,))
t1.daemon = True
t2 = Thread(target=showspots, args=(lock,))
t2.daemon = True
t3 = Thread(target=getvfo)
t3.daemon = True

t1.start()
t2.start()
t3.start()

t1.join()
t2.join()
t3.join()

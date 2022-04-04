#! /usr/bin/env python3
# pylint: disable=invalid-name
# pylint: disable=line-too-long
# pylint: disable=global-statement
"""
This is an RBN spot bandmap list which filters the spotters by distance.
If you limit the RBN spotting stations to those closest to you, you can
limit the reported spots to those you can actually have a chance to hear.
It does no good to get WFD CW spots from Italy if you're in Texas...
"""

import logging

import sqlite3
import re
import time
import argparse
from math import radians, sin, cos, atan2, sqrt
from threading import Thread, Lock
from sqlite3 import Error
from telnetlib import Telnet
from rich.console import Console
from rich import print  # pylint: disable=redefined-builtin
from rich.logging import RichHandler
from rich.traceback import install
from bs4 import BeautifulSoup as bs
import requests
from cat_interface import CAT


logging.basicConfig(
    level="CRITICAL",
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(rich_tracebacks=True)],
)


install(show_locals=True)


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
    "-C",
    "--cat",
    type=str,
    help="Type of CAT control flrig/rigctld. Default is: rigctld",
)
parser.add_argument(
    "-f", "--cathost", type=str, help="Hostname/IP of flrig. Default is: localhost"
)
parser.add_argument("-P", "--catport", type=int, help="flrig port. Default is: 4532")
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

if args.cat:
    cattype = args.cat
else:
    cattype = "rigctld"

if args.cathost:
    cathost = args.cathost
else:
    cathost = "localhost"

if args.catport:
    catport = args.catport
else:
    catport = 4532

if args.log:
    logdb = args.log
else:
    logdb = "FieldDay.db"

cat = CAT(cattype, cathost, catport)
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
            cursor = conn.cursor()
            sql = (
                "SELECT COUNT(*) as hascolumn "
                "FROM pragma_table_info('contacts') "
                "WHERE name='mode';"
            )
            cursor.execute(sql)
            hascolumn = cursor.fetchone()[0]
            if hascolumn:
                sql = "select * from contacts where mode='CW'"
            else:
                sql = "select * from contacts"
            cursor.execute(sql)
            result = cursor.fetchall()
            for contact in result:
                if hascolumn:
                    if logdb == "FieldDay.db":
                        _, callsign, _, _, _, _, band, _, _, _, _ = contact
                    else:
                        _, callsign, _, _, _, band, _, _, _, _ = contact
                else:
                    _, callsign, _, _, _, _, band, _, _ = contact
                if band in contactlist:
                    contactlist[band].append(callsign)
                else:
                    contactlist[band] = list()
                    contactlist[band].append(callsign)
    except Error as err:
        console.print(err)


def alreadyworked(callsign, band):
    """
    Check if callsign has already been worked on band.
    """
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
            vfo = float(cat.get_vfo()) / 1000
        except ConnectionRefusedError:
            vfo = 0.0
        time.sleep(0.25)


def comparevfo(freq):
    """
    Return the difference in khz between the VFO and the spot.
    Spots show up in Blue, Grey, Dark Grey, Black backgrounds depending on how far away you VFO is.
    """
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

    number_of_characters = len(maiden)
    if not 8 >= number_of_characters >= 2 and number_of_characters % 2 == 0:
        return 0, 0

    lon = (ord(maiden[0]) - 65) * 20 - 180
    lat = (ord(maiden[1]) - 65) * 10 - 90

    if number_of_characters >= 4:
        lon += (ord(maiden[2]) - 48) * 2
        lat += ord(maiden[3]) - 48

    if number_of_characters >= 6:
        lon += (ord(maiden[4]) - 65) / 12 + 1 / 24
        lat += (ord(maiden[5]) - 65) / 24 + 1 / 48

    if number_of_characters >= 8:
        lon += (ord(maiden[6])) * 5.0 / 600
        lat += (ord(maiden[7])) * 2.5 / 600

    return lat, lon


def getband(freq: str) -> str:
    """
    Convert a (string) frequency into a (string) band.
    Returns a (string) band.
    Returns a "0" if frequency is out of band.
    """
    try:
        frequency = int(float(freq)) * 1000
    except ValueError:
        frequency = 0
    if 2000000 > frequency > 1800000:
        return "160"
    if 4000000 > frequency > 3500000:
        return "80"
    if 5406000 > frequency > 5330000:
        return "60"
    if 7300000 > frequency > 7000000:
        return "40"
    if 10150000 > frequency > 10100000:
        return "30"
    if 14350000 > frequency > 14000000:
        return "20"
    if 18168000 > frequency > 18068000:
        return "17"
    if 21450000 > frequency > 21000000:
        return "15"
    if 24990000 > frequency > 24890000:
        return "12"
    if 29700000 > frequency > 28000000:
        return "10"
    if 54000000 > frequency > 50000000:
        return "6"
    if 148000000 > frequency > 144000000:
        return "2"

    return "0"


def calc_distance(grid1, grid2):
    """
    Takes two maidenhead gridsquares and returns the distance between the two in kilometers.
    """
    earth_radius = 6371
    lat1, long1 = gridtolatlon(grid1)
    lat2, long2 = gridtolatlon(grid2)

    d_lat = radians(lat2) - radians(lat1)
    d_long = radians(long2) - radians(long1)

    r_lat1 = radians(lat1)
    r_lat2 = radians(lat2)

    aye = sin(d_lat / 2) * sin(d_lat / 2) + cos(r_lat1) * cos(r_lat2) * sin(
        d_long / 2
    ) * sin(d_long / 2)
    cee = 2 * atan2(sqrt(aye), sqrt(1 - aye))
    dee = earth_radius * cee  # distance in km

    return dee


def inband(freq):
    """
    Returns True if the frequency is within the General portion of the band.
    """
    in_band = False
    if 2000 > freq > 1800:
        in_band = True
    if 3600 > freq > 3525:
        in_band = True
    if 4000 > freq > 3800:
        in_band = True
    if 7125 > freq > 7025:
        in_band = True
    if 7300 > freq > 7175:
        in_band = True
    if 10150 > freq > 10100:
        in_band = True
    if 14150 > freq > 14025:
        in_band = True
    if 14350 > freq > 14225:
        in_band = True
    if 18168 > freq > 18068:
        in_band = True
    if 21200 > freq > 21025:
        in_band = True
    if 21450 > freq > 21275:
        in_band = True
    if 24990 > freq > 24890:
        in_band = True
    if 29700 > freq > 28000:
        in_band = True
    if 54000 > freq > 50000:
        in_band = True
    return in_band


def add_spot(callsign, freq, band):
    """
    Removes spots older than value stored in spottoold.
    Inserts a new or updates existing spot.
    """
    with sqlite3.connect("spots.db") as conn:
        spot = (callsign, freq, band)
        cursor = conn.cursor()
        sql = (
            "delete from spots where Cast "
            "((JulianDay(datetime('now')) - JulianDay(date_time)) * 24 * 60 * 60 As Integer)"
            f" > {spottoold}"
        )
        cursor.execute(sql)
        conn.commit()
        sql = f"select count(*) from spots where callsign='{callsign}'"
        cursor.execute(sql)
        result = cursor.fetchall()
        if result[0][0] == 0:
            sql = (
                "INSERT INTO spots(callsign, date_time, frequency, band) "
                "VALUES(?,datetime('now'),?,?)"
            )
            cursor.execute(sql, spot)
            conn.commit()
        else:
            sql = (
                f"update spots set frequency='{freq}', "
                "date_time = datetime('now'), "
                f"band='{band}' "
                f"where callsign='{callsign}';"
            )
            cursor.execute(sql)
            conn.commit()


def pruneoldest():
    """
    Removes the oldest spot.
    """
    with sqlite3.connect("spots.db") as conn:
        cursor = conn.cursor()
        sql = "select * from spots order by date_time asc"
        cursor.execute(sql)
        result = cursor.fetchone()
        oldest_id, _, _, _, _ = result
        sql = f"delete from spots where id='{oldest_id}'"
        cursor.execute(sql)
        conn.commit()


def showspots(the_lock):
    """
    Show spot list, sorted by frequency.
    Prune the list if it's longer than the window by removing the oldest spots.
    If tracking your VFO highlight those spots in/near your bandpass.
    Mark those already worked in red.
    """
    while True:
        updatecontactlist()
        console.clear()
        console.rule(f"[bold red]Spots VFO: {vfo}")
        with the_lock:
            with sqlite3.connect("spots.db") as conn:
                cursor = conn.cursor()
                sql = (
                    "select *, Cast "
                    "((JulianDay(datetime('now')) - JulianDay(date_time))"
                    " * 24 * 60 * 60 As Integer) "
                    "from spots order by frequency asc"
                )
                cursor.execute(sql)
                result = cursor.fetchall()
        offset = 3
        for spot_number, spot in enumerate(result):
            _, callsign, date_time, frequency, band, delta = spot
            if (spot_number + offset) > console.height:
                with the_lock:
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
                    f"{callsign.ljust(11)} "
                    f"{str(frequency).rjust(8)} "
                    f"{str(band).rjust(3)}M "
                    f"{date_time.split()[1]} "
                    f"{delta}",
                    style=style,
                    overflow="ellipsis",
                )
        time.sleep(1)


def getrbn(the_lock):
    """loginto and pull info from the rbns"""
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
                if not inband(float(freq)) and showoutofband is False:
                    continue
                if band in limitband:
                    with the_lock:
                        add_spot(callsign, freq, band)


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
    found_spotter = datum[0].a.contents[0].strip()
    bands = datum[1].contents[0].strip()
    grid = datum[2].contents[0]
    distance = calc_distance(grid, mygrid) / 1.609
    if distance < maxspotterdistance:
        localspotters.append(found_spotter)

print(f"Spotters with in {maxspotterdistance} mi:")
print(f"{localspotters}")
time.sleep(1)
with sqlite3.connect("spots.db") as connection:
    the_cursor = connection.cursor()
    SQL_COMMAND = (
        "CREATE TABLE IF NOT EXISTS spots"
        "(id INTEGER PRIMARY KEY, "
        "callsign text, "
        "date_time text NOT NULL, "
        "frequency REAL NOT NULL, "
        "band INTEGER);"
    )
    the_cursor.execute(SQL_COMMAND)
    sql_command = (
        "delete from spots where "
        "Cast ((JulianDay(datetime('now')) - JulianDay(date_time)) * 24 * 60 * 60 As Integer) "
        f"> {spottoold}"
    )
    the_cursor.execute(sql_command)
    connection.commit()

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

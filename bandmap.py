#! /usr/bin/env python3

import xmlrpc.client
import requests
import sqlite3
from sqlite3 import Error
from telnetlib import Telnet
from rich.console import Console
from rich import print
from bs4 import BeautifulSoup as bs
from math import radians, sin, cos, atan2, sqrt

server = xmlrpc.client.ServerProxy("http://localhost:12345")
limitband = ('160','80','40','30','20','17','15','12','10','6')
showoutofband = False
spottoold = 600
console = Console(width=38)
localspotters = list()
maxspotterdistance = 500
mygrid = "DM13AT"
vfo = 0.0
oldvfo = 0.0
contactlist = dict()

def updatecontactlist():
    global contactlist
    contactlist = dict()
    try:
        with sqlite3.connect("FieldDay.db") as fd:
            c = fd.cursor()
            sql="select * from contacts where mode='CW'"
            c.execute(sql)
            result = c.fetchall()
            for contact in result:
                _, callsign, _, _, _, _, band, _, _, _ , _ = contact
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
    Get the freq from the active VFO in khz
    """
    global vfo
    try:
        vfo = float(server.rig.get_vfo()) / 1000
    except:
        vfo = 0.0

def comparevfo(freq):
    """
    Return the difference in khz between the VFO and the spot.
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
    maiden = str(maiden).strip().upper()

    N = len(maiden)
    if not 8 >= N >= 2 and N % 2 == 0:
        return 0,0

    lon = (ord(maiden[0]) - 65) * 20 - 180
    lat = (ord(maiden[1]) - 65) * 10 - 90

    if N >= 4:
        lon += (ord(maiden[2])-48) * 2
        lat += (ord(maiden[3])-48)

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
    R = 6371 #earh radius
    lat1, long1 = gridtolatlon(grid1)
    lat2, long2 = gridtolatlon(grid2)

    d_lat = radians(lat2) - radians(lat1)
    d_long = radians(long2) - radians(long1)

    r_lat1 = radians(lat1)
    r_long1 = radians(long1)
    r_lat2 = radians(lat2)
    r_long2 = radians(long2)

    a = sin(d_lat/2) * sin(d_lat/2) + cos(r_lat1) * cos(r_lat2) * sin(d_long/2) * sin(d_long/2)
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    d = R * c #distance in km

    return d

def inband(freq):
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

def addSpot(conn, callsign, freq, band):
    global spottoold
    spot = (callsign, freq, band)
    c=conn.cursor()
    sql=f"delete from spots where Cast ((JulianDay(datetime('now')) - JulianDay(date_time)) * 24 * 60 * 60 As Integer) > {spottoold}"
    c.execute(sql)
    conn.commit()
    sql=f"select count(*) from spots where callsign='{callsign}'"
    c.execute(sql)
    result = c.fetchall()
    if result[0][0] == 0:
        sql = "INSERT INTO spots(callsign, date_time, frequency, band) VALUES(?,datetime('now'),?,?)"
        c.execute(sql, spot)
        conn.commit()
        console.print(f"addSpot: Insert: {sql}")
        showspots(conn)
    else:
        sql = f"update spots set frequency='{freq}', date_time = datetime('now'), band='{band}' where callsign='{callsign}';"
        c.execute(sql)
        conn.commit()

def pruneoldest(conn):
    c=conn.cursor()
    sql="select * from spots order by date_time asc"
    c.execute(sql)
    result = c.fetchone()
    id, _, _, _, _ = result
    sql=f"delete from spots where id='{id}'"
    c.execute(sql)
    conn.commit()

def showspots(conn):
    global vfo
    console.clear()
    console.rule(f"[bold red]Spots")
    updatecontactlist()
    c=conn.cursor()
    sql="select *, Cast ((JulianDay(datetime('now')) - JulianDay(date_time)) * 24 * 60 * 60 As Integer) from spots order by frequency asc"
    c.execute(sql)
    result = c.fetchall()
    displayed = 2
    for x, spot in enumerate(result):
        _, callsign, date_time, frequency, band, delta = spot
        displayed += 1
        if displayed > console.height: 
            pruneoldest(conn)
        else:
            if inband(frequency):
                style = ""
            else:
                style = "strike"
            if comparevfo(frequency) < 0.8:
                style = "bold on color(237)"
            if comparevfo(frequency) < 0.5:
                style = "bold on color(240)"
            if comparevfo(frequency) < 0.2:
                style = "bold on blue"
            if alreadyworked(callsign, band):
                style = "bold on color(88)"
            console.print(f"{callsign.ljust(11)} {str(frequency).rjust(8)} {str(band).rjust(3)}M {date_time.split()[1]} {delta}", style=style, overflow="ellipsis")

console.clear()
updatecontactlist()
console.rule("[bold red]Finding Spotters")
page = requests.get("http://reversebeacon.net/cont_includes/status.php?t=skt", timeout = 10.0)
soup = bs(page.text, 'lxml')
rows = soup.find_all('tr', {'class': "online"})
for row in rows:
    datum = row.find_all('td')
    spotter = datum[0].a.contents[0].strip()
    bands = datum[1].contents[0].strip()
    grid = datum[2].contents[0]
    distance = calc_distance(grid, mygrid)/1.609
    if distance < maxspotterdistance:
        BandList = [int(x[:-1]) for x in bands.split(',') if x in '160m 80m 60m 40m 30m 20m 17m 15m 12m 10m 6m'.split()]
        #print(f"Spotter: {spotter}, Grid: {grid}, Distance: {distance}mi, Bands: {BandList}")
        localspotters.append(f"{spotter}-#:")

print(f"Spotters with in {maxspotterdistance} mi:")
print(f"{localspotters}")

with sqlite3.connect(":memory:") as conn:
    c = conn.cursor()
    sql_table = """CREATE TABLE IF NOT EXISTS spots (id INTEGER PRIMARY KEY, callsign text, date_time text NOT NULL, frequency REAL NOT NULL, band INTEGER);"""
    c.execute(sql_table)
    conn.commit()
    #skimmer.skccgroup.com 7000
    #'dxc.nc7j.com', 23
    with Telnet('skimmer.skccgroup.com', 7000) as tn:
        tn.read_until(b'ogin:', timeout=2.0)
        tn.write("k6gte\r\n".encode('ascii'))
        tn.read_until(b'sign:', timeout=1.0)
        #tn.write("k6gte\r\n".encode('ascii'))
        while True:
            line=tn.read_until(b'\r\n', timeout=1.0)
            if line != b'':
                spot = line.decode().split()
                if not spot[2] in localspotters:
                    continue
                callsign = spot[4]
                try:
                    freq = spot[3]
                except:
                    continue
                band = getband(freq)
                if not inband(float(freq)) and showoutofband == False:
                    continue
                if band in limitband:
                    addSpot(conn, callsign, freq, band)
                getvfo()
                if vfo != oldvfo:
                    oldvfo = vfo
                    showspots(conn)
            else:
                getvfo()
                showspots(conn)
           

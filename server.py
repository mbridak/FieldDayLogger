#!/usr/bin/env python3
"""This is the description"""

# from cmath import log
import curses
from curses import wrapper
from curses.textpad import rectangle
import logging
import socket
import time
from time import gmtime, strftime
import os
import sys
import threading

from json import JSONDecodeError, loads, dumps
from pathlib import Path
from lib.server_database import DataBase
from lib.version import __version__

# from lib.settings import Settings
# pylint: disable=no-name-in-module
# pylint: disable=c-extension-no-member


if Path("./debug").exists():
    logging.basicConfig(
        filename="server_debug.log",
        filemode="w+",
        format=(
            "[%(asctime)s] %(levelname)s %(module)s - "
            "%(funcName)s Line %(lineno)d: %(message)s"
        ),
        datefmt="%H:%M:%S",
        level=logging.DEBUG,
    )
    logging.debug("Debug started")
else:
    logging.basicConfig(level=logging.CRITICAL)


class Trafficlog:
    """holds recent udp log traffic"""

    def __init__(self):
        self.items = []

    def add_item(self, item):
        """adds an item to the log and trims the log"""
        self.items.append(item)
        if len(self.items) > 9:
            self.items = self.items[1 : len(self.items)]

    def get_log(self):
        """returns a list of log items"""
        return self.items


DB = DataBase("server_database.db")

MULTICAST_PORT = 2239
MULTICAST_GROUP = "224.1.1.1"
INTERFACE_IP = "0.0.0.0"

OURCALL = "XXXX"
OURCLASS = "XX"
OURSECTION = "XXX"
ALTPOWER = 0
log = Trafficlog()
THE_SCREEN = curses.initscr()

height, width = THE_SCREEN.getmaxyx()
if height < 24 or width < 80:
    print("Terminal size needs to be at least 80x24")
    curses.endwin()
    sys.exit()

try:
    if os.path.exists("./server_preferences.json"):
        with open(
            "./server_preferences.json", "rt", encoding="utf-8"
        ) as file_descriptor:
            preference = loads(file_descriptor.read())
            logging.info("%s", preference)
            MULTICAST_PORT = preference.get("multicast_port")
            MULTICAST_GROUP = preference.get("mullticast_group")
            INTERFACE_IP = preference.get("interface_ip")
            OURCALL = preference.get("ourcall")
            OURCLASS = preference.get("ourclass")
            OURSECTION = preference.get("oursection")
            ALTPOWER = preference.get("altpower")
    else:
        print("-=* No Settings File Using Defaults *=-")
except IOError as exception:
    logging.critical("%s", exception)


def send_pulse():
    """send heartbeat"""
    while True:
        pulse = b'{"cmd": "PING", "host": "server"}'
        s.sendto(pulse, (MULTICAST_GROUP, MULTICAST_PORT))
        time.sleep(10)


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("", MULTICAST_PORT))
mreq = socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton(INTERFACE_IP)
s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, bytes(mreq))


_heartbeat = threading.Thread(
    target=send_pulse,
    daemon=True,
)
_heartbeat.start()

people = {}


def comm_log():
    """Display recent UDP traffic"""
    try:
        logwindow = curses.newwin(10, 49, 9, 1)
        # rectangle(THE_SCREEN, 8,0,20,50)
        logwindow.clear()
        for display_line, display_item in enumerate(log.get_log()):
            logwindow.addstr(display_line, 0, display_item)
        logwindow.refresh()
    except curses.error as err:
        logging.debug("%s", err)
    bands = ["160", "80", "40", "20", "15", "10", "6", "2"]
    blist = []
    list_o_bands = DB.get_bands()
    if list_o_bands:
        for count in list_o_bands:
            blist.append(count[0])
    quewindow = curses.newwin(11, 26, 9, 52)
    quewindow.clear()
    quewindow.addstr(0, 0, "Band   CW    PH    DI\n")
    for band in bands:
        if band in blist:
            cwt = DB.get_band_mode_tally(band, "CW")
            dit = DB.get_band_mode_tally(band, "DI")
            pht = DB.get_band_mode_tally(band, "PH")
            line = (
                f"{str(band).rjust(4, ' ')} "
                f"{str(cwt[0]).rjust(5, ' ')} "
                f"{str(pht[0]).rjust(5, ' ')} "
                f"{str(dit[0]).rjust(5, ' ')}\n"
            )
            quewindow.addstr(line)
    THE_SCREEN.refresh()
    quewindow.refresh()


def main(_):
    """Main loop"""
    os.environ.setdefault("ESCDELAY", "25")
    curses.set_tabsize(4)
    curses.start_color()
    curses.use_default_colors()
    if curses.can_change_color():
        curses.init_color(curses.COLOR_MAGENTA, 1000, 640, 0)
        curses.init_color(curses.COLOR_BLACK, 0, 0, 0)
        curses.init_color(curses.COLOR_CYAN, 500, 500, 500)
        curses.init_pair(1, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_RED, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.noecho()
    curses.cbreak()

    THE_SCREEN.addstr(0, 0, f"\t\t\t\t\tField Day aggregation server v{__version__}\n")
    THE_SCREEN.addstr("   Group information                      Network Information\n")
    THE_SCREEN.addstr(2, 40, f"Multicast Group: {MULTICAST_GROUP}")
    THE_SCREEN.addstr(3, 40, f"Multicast Port:  {MULTICAST_PORT}")
    THE_SCREEN.addstr(4, 40, f"Interface IP:    {INTERFACE_IP}")

    THE_SCREEN.addstr(2, 1, f"Call:     {OURCALL}")
    THE_SCREEN.addstr(3, 1, f"Class:    {OURCLASS}")
    THE_SCREEN.addstr(4, 1, f"Section:  {OURSECTION}")
    THE_SCREEN.addstr(5, 1, f"AltPower: {bool(ALTPOWER)}")
    rectangle(THE_SCREEN, 8, 0, 20, 50)
    rectangle(THE_SCREEN, 8, 51, 20, 79)
    THE_SCREEN.refresh()
    while 1:
        try:
            payload = s.recv(1500)
            try:
                json_data = loads(payload.decode())
            except UnicodeDecodeError as err:
                the_error = f"Not Unicode: {err}\n{payload}\n"
                logging.debug(the_error)
                continue
            except JSONDecodeError as err:
                the_error = f"Not JSON: {err}\n{payload}\n"
                logging.debug(the_error)
                continue
            logging.debug("%s", json_data)
            timestamp = strftime("%H:%M:%S", gmtime())
            if json_data.get("cmd") == "POST":

                DB.log_contact(
                    (
                        json_data.get("unique_id"),
                        json_data.get("hiscall"),
                        json_data.get("class"),
                        json_data.get("section"),
                        json_data.get("frequency"),
                        json_data.get("band"),
                        json_data.get("mode"),
                        json_data.get("power"),
                        json_data.get("grid"),
                        json_data.get("opname"),
                        json_data.get("station"),
                    )
                )
                log.add_item(
                    f"[{timestamp}] New Contact "
                    f"{json_data.get('station')}: "
                    f"{json_data.get('hiscall')} "
                    f"{json_data.get('band')}M "
                    f"{json_data.get('mode')}"
                )
                comm_log()
                packet = {"cmd": "RESPONSE"}
                packet["recipient"] = json_data.get("station")
                packet["subject"] = "POST"
                packet["unique_id"] = json_data.get("unique_id")
                bytes_to_send = bytes(dumps(packet), encoding="ascii")
                s.sendto(bytes_to_send, (MULTICAST_GROUP, MULTICAST_PORT))
                log.add_item(f"[{timestamp}] CONFIRM POST: {json_data.get('station')}")
                comm_log()
                continue

            if json_data.get("cmd") == "GET":
                log.add_item(f"[{timestamp}] {json_data}")
                comm_log()
                continue

            if json_data.get("cmd") == "DELETE":
                log.add_item(f"[{timestamp}] Deleting: {json_data.get('unique_id')}")
                DB.delete_contact(json_data.get("unique_id"))
                comm_log()
                packet = {"cmd": "RESPONSE"}
                packet["recipient"] = json_data.get("station")
                packet["subject"] = "DELETE"
                packet["unique_id"] = json_data.get("unique_id")
                bytes_to_send = bytes(dumps(packet), encoding="ascii")
                s.sendto(bytes_to_send, (MULTICAST_GROUP, MULTICAST_PORT))
                log.add_item(
                    f"[{timestamp}] CONFIRM DELETE: {json_data.get('station')}"
                )
                comm_log()
                continue

            if json_data.get("cmd") == "UPDATE":
                log.add_item(
                    f"[{timestamp}] Updating "
                    f"{json_data.get('unique_id')} "
                    f"{json_data.get('hiscall')} "
                    f"{json_data.get('band')} "
                    f"{json_data.get('mode')}"
                )
                DB.change_contact(
                    (
                        json_data.get("hiscall"),
                        json_data.get("class"),
                        json_data.get("section"),
                        json_data.get("date_time"),
                        json_data.get("band"),
                        json_data.get("mode"),
                        json_data.get("power"),
                        json_data.get("station"),
                        json_data.get("frequency"),
                        json_data.get("unique_id"),
                    )
                )
                comm_log()
                packet = {"cmd": "RESPONSE"}
                packet["recipient"] = json_data.get("station")
                packet["subject"] = "UPDATE"
                packet["unique_id"] = json_data.get("unique_id")
                bytes_to_send = bytes(dumps(packet), encoding="ascii")
                s.sendto(bytes_to_send, (MULTICAST_GROUP, MULTICAST_PORT))
                log.add_item(
                    f"[{timestamp}] CONFIRM UPDATE: {json_data.get('station')}"
                )
                comm_log()
                continue

            if json_data.get("cmd") == "PING":
                if not json_data.get("host"):
                    log.add_item(
                        f"[{timestamp}] Ping: {json_data.get('station')} "
                        f"{json_data.get('band')}M {json_data.get('mode')}"
                    )
                    if json_data.get("station"):
                        band_mode = f"{json_data.get('band')} {json_data.get('mode')}"
                        if people.get(json_data.get("station")) != band_mode:
                            people[json_data.get("station")] = band_mode
                comm_log()
                continue

            if json_data.get("cmd") == "GROUPQUERY":
                packet = {"cmd": "RESPONSE"}
                packet["recipient"] = json_data.get("station")
                packet["subject"] = "HOSTINFO"
                packet["groupcall"] = OURCALL
                packet["groupclass"] = OURCLASS
                packet["groupsection"] = OURSECTION
                bytes_to_send = bytes(dumps(packet), encoding="ascii")
                s.sendto(bytes_to_send, (MULTICAST_GROUP, MULTICAST_PORT))
                log.add_item(f"[{timestamp}] GROUPQUERY: {json_data.get('station')}")
                comm_log()

        except UnicodeDecodeError as err:
            print(f"[{timestamp}] Not JSON: {err}\n{payload}\n")
        except JSONDecodeError as err:
            print(f"[{timestamp}] Not JSON: {err}\n{payload}\n")


wrapper(main)

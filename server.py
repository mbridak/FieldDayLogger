#!/usr/bin/env python3
"""This is the description"""

# COLOR_BLACK	Black
# COLOR_BLUE	Blue
# COLOR_CYAN	Cyan (light greenish blue)
# COLOR_GREEN	Green
# COLOR_MAGENTA	Magenta (purplish red)
# COLOR_RED	Red
# COLOR_WHITE	White
# COLOR_YELLOW	Yellow

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
import argparse

from itertools import chain
from json import JSONDecodeError, loads, dumps
from pathlib import Path
from lib.server_database import DataBase
from lib.version import __version__

# from lib.settings import Settings
# pylint: disable=no-name-in-module, invalid-name, c-extension-no-member, global-statement


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

parser = argparse.ArgumentParser(description="Field Day aggregation server.")
parser.add_argument("-l", "--log", action="store_true", help="Generate log")

args = parser.parse_args()


class Trafficlog:
    """holds recent udp log traffic"""

    def __init__(self):
        self.items = []

    def add_item(self, item):
        """adds an item to the log and trims the log"""
        self.items.append(item)
        if len(self.items) > 16:
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
BATTERYPOWER = 0
QRP = 0
HIGHPOWER = 0
NAME = "Hiram Maxim"
ADDRESS = "225 Main Street"
CITY = "Newington"
STATE = "CT"
POSTALCODE = "06111"
COUNTRY = "USA"
EMAIL = "Hiram.Maxim@arrl.net"

POINTS = 0
LASTHOUR = 0
LAST15 = 0

LOG = Trafficlog()
THE_SCREEN = curses.initscr()
LOGWINDOW = curses.newwin(16, 49, 7, 1)
QUEWINDOW = curses.newwin(9, 26, 7, 52)
PEOPLEWINDOW = curses.newwin(6, 28, 17, 51)

people = {}


height, width = THE_SCREEN.getmaxyx()
if height < 24 or width < 80:
    print("Terminal size needs to be at least 80x24")
    curses.endwin()
    sys.exit()

try:
    if os.path.exists("./server_preferences.json"):
        with open(
            "./server_preferences.json", "rt", encoding="utf-8"
        ) as _file_descriptor:
            preference = loads(_file_descriptor.read())
            logging.info("%s", preference)
            MULTICAST_PORT = preference.get("multicast_port")
            MULTICAST_GROUP = preference.get("mullticast_group")
            INTERFACE_IP = preference.get("interface_ip")
            OURCALL = preference.get("ourcall")
            OURCLASS = preference.get("ourclass")
            OURSECTION = preference.get("oursection")
            BATTERYPOWER = preference.get("batterypower")
            NAME = preference.get("name")
            ADDRESS = preference.get("address")
            CITY = preference.get("city")
            STATE = preference.get("state")
            POSTALCODE = preference.get("postalcode")
            COUNTRY = preference.get("country")
            EMAIL = preference.get("email")
    else:
        print("-=* No Settings File Using Defaults *=-")
except IOError as exception:
    logging.critical("%s", exception)


def prectangle(win, uly, ulx, lry, lrx):
    """Draw a rectangle with corners at the provided upper-left
    and lower-right coordinates.
    """
    win.vline(uly + 1, ulx, curses.ACS_VLINE, lry - uly - 1)
    win.hline(uly, ulx + 1, curses.ACS_HLINE, lrx - ulx - 1)
    win.hline(lry, ulx + 1, curses.ACS_HLINE, lrx - ulx - 1)
    win.vline(uly + 1, lrx, curses.ACS_VLINE, lry - uly - 1)
    win.addch(uly, ulx, curses.ACS_LTEE)  # UL
    win.addch(uly, lrx, curses.ACS_RTEE)  # UR
    try:
        win.addch(lry, lrx, curses.ACS_LRCORNER)  # LR
    except curses.error:
        pass
    win.addch(lry, ulx, curses.ACS_BTEE)  # LL
    win.vline(1, 0, curses.ACS_VLINE, 5)
    win.vline(1, 79, curses.ACS_VLINE, 5)
    win.vline(1, 22, curses.ACS_VLINE, 5)
    win.vline(1, 58, curses.ACS_VLINE, 5)
    win.addch(6, 0, curses.ACS_LTEE)
    win.addch(6, 79, curses.ACS_RTEE)
    win.addch(6, 50, curses.ACS_TTEE)
    win.addch(6, 58, curses.ACS_BTEE)
    win.addch(6, 22, curses.ACS_BTEE)


def ptitle(win, y, x1, x2, title):
    """Prints title"""
    title_length = len(title)
    middle_window = x2 - (x2 - x1) / 2
    x = int(middle_window - (title_length / 2))
    win.addstr(y, x, title, curses.color_pair(7))
    win.addch(y, x - 1, curses.ACS_RTEE)
    win.addch(y, x + title_length, curses.ACS_LTEE)


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


def comm_log():
    """Display recent UDP traffic"""
    try:
        LOGWINDOW.clear()
        # LOGWINDOW.box()
        for display_line, display_item in enumerate(LOG.get_log()):
            LOGWINDOW.addstr(display_line, 0, display_item)
        LOGWINDOW.refresh()
    except curses.error as err:
        logging.debug("%s", err)
    bands = ["160", "80", "40", "20", "15", "10", "6", "2"]
    blist = []
    list_o_bands = DB.get_bands()
    if list_o_bands:
        for count in list_o_bands:
            blist.append(count[0])
    QUEWINDOW.clear()
    # QUEWINDOW.box()
    QUEWINDOW.addstr(0, 0, "Band   CW    PH    DI", curses.color_pair(1))
    for yline, band in enumerate(bands):
        cwt = DB.get_band_mode_tally(band, "CW")
        dit = DB.get_band_mode_tally(band, "DI")
        pht = DB.get_band_mode_tally(band, "PH")
        line = (
            f"{str(band).rjust(4, ' ')} "
            f"{str(cwt[0]).rjust(5, ' ')} "
            f"{str(pht[0]).rjust(5, ' ')} "
            f"{str(dit[0]).rjust(5, ' ')}"
        )
        QUEWINDOW.addstr(yline + 1, 0, line)
    THE_SCREEN.refresh()
    QUEWINDOW.refresh()


def show_people():
    """Display operators"""
    rev_dict = {}
    for key, value in people.items():
        rev_dict.setdefault(value, set()).add(key)
    result = set(
        chain.from_iterable(
            values for key, values in rev_dict.items() if len(values) > 1
        )
    )
    PEOPLEWINDOW.clear()
    xcol = 0
    for yline, op_callsign in enumerate(people.keys()):
        if yline > 5:
            yline -= 6
            xcol = 15
        try:
            if op_callsign in result:
                PEOPLEWINDOW.addnstr(
                    yline,
                    xcol,
                    f"{op_callsign.rjust(6,' ')} {people.get(op_callsign).rjust(6, ' ')}",
                    13,
                    curses.color_pair(2) | curses.A_BOLD,
                )
            else:
                PEOPLEWINDOW.addnstr(
                    yline,
                    xcol,
                    f"{op_callsign.rjust(6,' ')} {people.get(op_callsign).rjust(6, ' ')}",
                    13,
                )
        except curses.error:
            logging.debug("yline: %d xcol: %d", yline, xcol)
    THE_SCREEN.refresh()
    PEOPLEWINDOW.refresh()


def get_stats():
    """Get statistics"""
    global QRP
    (
        cwcontacts,
        phonecontacts,
        digitalcontacts,
        _,
        last15,
        lasthour,
        _,
        QRP,
    ) = DB.stats()

    points = (int(cwcontacts) * 2) + (int(digitalcontacts) * 2) + int(phonecontacts)

    score = (((QRP * 3) * BATTERYPOWER) + 2) * points

    THE_SCREEN.addstr(2, 73, f"{score}", curses.color_pair(7))
    THE_SCREEN.addstr(3, 73, f"{lasthour}", curses.color_pair(7))
    THE_SCREEN.addstr(4, 73, f"{last15}", curses.color_pair(7))


def fakefreq(band, mode):
    """
    If unable to obtain a frequency from the rig,
    This will return a sane value for a frequency mainly for the cabrillo and adif log.
    Takes a band and mode as input and returns freq in khz.
    """
    logging.info("fakefreq: band:%s mode:%s", band, mode)
    modes = {"CW": 0, "DI": 1, "PH": 2, "FT8": 1, "SSB": 2}
    fakefreqs = {
        "160": ["1830", "1805", "1840"],
        "80": ["3530", "3559", "3970"],
        "60": ["5332", "5373", "5405"],
        "40": ["7030", "7040", "7250"],
        "30": ["10130", "10130", "0000"],
        "20": ["14030", "14070", "14250"],
        "17": ["18080", "18100", "18150"],
        "15": ["21065", "21070", "21200"],
        "12": ["24911", "24920", "24970"],
        "10": ["28065", "28070", "28400"],
        "6": ["50.030", "50300", "50125"],
        "2": ["144030", "144144", "144250"],
        "222": ["222100", "222070", "222100"],
        "432": ["432070", "432200", "432100"],
        "SAT": ["144144", "144144", "144144"],
    }
    freqtoreturn = fakefreqs[band][modes[mode]]
    logging.info("fakefreq: returning:%s", freqtoreturn)
    return freqtoreturn


def calcscore():
    """
    Return our current score based on operating power,
    battery power and types of contacts.

    2022 scoring: contacts over 100w are disallowed.
    QRP and Low Power (<100W) have base multiplier of 2.
    QRP with Battery Power has base multiplier of 5
    """
    global QRP
    QRP, _ = DB.qrp_check()
    c_dubs, phone, digital = DB.contacts_under_101watts()
    score = (int(c_dubs) * 2) + int(phone) + (int(digital) * 2)
    multiplier = 2
    if QRP and BATTERYPOWER:
        multiplier = 5
    score = score * multiplier
    return score


def cabrillo():
    """
    Generates a cabrillo log file.
    """
    filename = f"./{OURCALL}.log"
    log = DB.fetch_all_contacts_asc()
    if not log:
        return
    catpower = ""
    if QRP:
        catpower = "QRP"
    elif HIGHPOWER:
        catpower = "HIGH"
    else:
        catpower = "LOW"
    try:
        with open(filename, "w", encoding="ascii") as file_descriptor:
            print("START-OF-LOG: 3.0", end="\r\n", file=file_descriptor)
            print(
                "CREATED-BY: K6GTE Field Day Logger",
                end="\r\n",
                file=file_descriptor,
            )
            print("CONTEST: ARRL-FD", end="\r\n", file=file_descriptor)
            print(
                f"CALLSIGN: {OURCALL}",
                end="\r\n",
                file=file_descriptor,
            )
            print(
                f"LOCATION: {OURSECTION}",
                end="\r\n",
                file=file_descriptor,
            )
            print(
                f"CATEGORY: {OURCLASS}",
                end="\r\n",
                file=file_descriptor,
            )

            print("CATEGORY-BAND: ALL", end="\r\n", file=file_descriptor)
            print("CATEGORY-MODE: MIXED", end="\r\n", file=file_descriptor)
            print("CATEGORY-OPERATOR: MULTI-OP", end="\r\n", file=file_descriptor)
            print("CATEGORY-STATION: PORTABLE", end="\r\n", file=file_descriptor)
            print(f"CATEGORY-POWER: {catpower}", end="\r\n", file=file_descriptor)
            print("CLUB: Test club", end="\r\n", file=file_descriptor)

            print(f"NAME: {NAME}", end="\r\n", file=file_descriptor)
            print(f"ADDRESS: {ADDRESS}", end="\r\n", file=file_descriptor)
            print(f"ADDRESS-CITY: {CITY}", end="\r\n", file=file_descriptor)
            print(f"ADDRESS-STATE: {STATE}", end="\r\n", file=file_descriptor)
            print(f"ADDRESS-POSTALCODE: {POSTALCODE}", end="\r\n", file=file_descriptor)
            print(f"ADDRESS-COUNTRY: {COUNTRY}", end="\r\n", file=file_descriptor)
            print(f"EMAIL: {EMAIL}", end="\r\n", file=file_descriptor)
            ops = DB.get_operators()
            operator_list = []
            for operators in ops:
                operator_list.append(operators[0])
            print(
                f"OPERATORS: {' '.join(operator_list)}",
                f"@{OURCALL}",
                end="\r\n",
                file=file_descriptor,
            )

            bonus_title = {
                "emergency_power": "100% Emergency Power",
                "media_publicity": "Media Publicity",
                "public_location": "Public Location",
                "public_info_table": "Public Information Table",
                "message_to_section_manager": "Message Origination to Section Manager",
                "message_handling": "Message Handling",
                "satellite_qso": "Satellite QSO",
                "alternate_power": "Alternate Power",
                "w1aw_bulletin": "W1AW Bulletin",
                "educational_activity": "Educational activity",
                "elected_official_visit": "Site Visitation by an elected governmental official",
                "agency_representative_visit": "Site Visitation by a representative of an agency",
                "gota": "GOTA",
                "web_submission": "Web submission",
                "youth_participation": "Field Day Youth Participation",
                "social_media": "Social Media",
                "safety_officer": "Safety Officer",
            }

            bonuses = preference.get("bonus")
            bonus_points = 0
            for bonus in bonuses:
                if bonus == "emergency_power":
                    if bonuses.get("emergency_power").get("bool"):
                        print(
                            f"SOAPBOX: {bonus_title.get(bonus)} Bonus 100 Points x "
                            f"{bonuses.get('emergency_power').get('station_count')}",
                            end="\r\n",
                            file=file_descriptor,
                        )
                        bonus_points += 100 * int(
                            bonuses.get("emergency_power").get("station_count")
                        )
                    continue

                if bonus == "message_handling":
                    if bonuses.get("message_handling").get("bool"):
                        print(
                            f"SOAPBOX: {bonus_title.get(bonus)} Bonus 10 Points x "
                            f"{bonuses.get('message_handling').get('message_count')}",
                            end="\r\n",
                            file=file_descriptor,
                        )
                        bonus_points += 10 * int(
                            bonuses.get("message_handling").get("message_count")
                        )
                    continue

                if bonus == "web_submission":
                    if bonuses[bonus]:
                        print(
                            f"SOAPBOX: {bonus_title.get(bonus)} Bonus 50 Points",
                            end="\r\n",
                            file=file_descriptor,
                        )
                        bonus_points += 50
                        continue

                if bonus == "youth_participation":
                    if bonuses.get("youth_participation").get("bool"):
                        print(
                            f"SOAPBOX: {bonus_title.get(bonus)} Bonus 20 Points x "
                            f"{bonuses.get('youth_participation').get('youth_count')}",
                            end="\r\n",
                            file=file_descriptor,
                        )
                        bonus_points += 20 * int(
                            bonuses.get("youth_participation").get("youth_count")
                        )
                    continue

                if bonuses[bonus]:
                    print(
                        f"SOAPBOX: {bonus_title.get(bonus)} Bonus 100 Points",
                        end="\r\n",
                        file=file_descriptor,
                    )
                    bonus_points += 100

            print(
                f"SOAPBOX: Total bonus points: {bonus_points}",
                end="\r\n",
                file=file_descriptor,
            )

            print(
                f"CLAIMED-SCORE: {calcscore() + bonus_points}",
                end="\r\n",
                file=file_descriptor,
            )

            for contact in log:
                (
                    _,
                    _,
                    hiscall,
                    hisclass,
                    hissection,
                    the_datetime,
                    freq,
                    band,
                    mode,
                    _,
                    _,
                    _,
                    _,
                ) = contact
                if mode == "DI":
                    mode = "DG"
                loggeddate = the_datetime[:10]
                loggedtime = the_datetime[11:13] + the_datetime[14:16]
                try:
                    temp = str(freq / 1000000).split(".")
                    freq = temp[0] + temp[1].ljust(3, "0")[:3]
                except TypeError:
                    freq = "UNKNOWN"
                if freq == "0000":
                    freq = fakefreq(band, mode)
                print(
                    f"QSO: {freq.rjust(6)} {mode} {loggeddate} {loggedtime} "
                    f"{OURCALL} {OURCLASS} "
                    f"{OURSECTION} {hiscall} "
                    f"{hisclass} {hissection}",
                    end="\r\n",
                    file=file_descriptor,
                )
            print("END-OF-LOG:", end="\r\n", file=file_descriptor)
    except IOError as err:
        logging.critical("cabrillo: IO error: %s, writing to %s", err, filename)
        return


def main(_):
    """Main loop"""
    os.environ.setdefault("ESCDELAY", "25")
    curses.curs_set(0)
    curses.set_tabsize(4)
    curses.start_color()
    curses.use_default_colors()
    if curses.can_change_color():
        curses.init_color(curses.COLOR_MAGENTA, 1000, 640, 0)
        curses.init_color(curses.COLOR_BLACK, 0, 0, 0)
        curses.init_color(curses.COLOR_CYAN, 500, 500, 500)
        curses.init_pair(1, curses.COLOR_MAGENTA, -1)
        curses.init_pair(2, curses.COLOR_RED, -1)
        curses.init_pair(3, curses.COLOR_CYAN, -1)
        curses.init_pair(4, curses.COLOR_GREEN, -1)
        curses.init_pair(5, curses.COLOR_BLUE, -1)
        curses.init_pair(6, curses.COLOR_YELLOW, -1)
        curses.init_pair(7, curses.COLOR_WHITE, -1)
        curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_MAGENTA)
    curses.noecho()
    curses.cbreak()
    THE_SCREEN.attron(curses.color_pair(8))
    line = f"Field Day aggregation server v{__version__}".center(width, " ")
    THE_SCREEN.addstr(0, 0, line)
    THE_SCREEN.attron(curses.color_pair(1))
    THE_SCREEN.addstr(
        1,
        0,
        "   Group information           Network Information                Scoring\n",
    )

    THE_SCREEN.addstr(2, 2, "Call____:")
    THE_SCREEN.addstr(f" {OURCALL}", curses.color_pair(7))
    THE_SCREEN.addstr(3, 2, "Class___:")
    THE_SCREEN.addstr(f" {OURCLASS}", curses.color_pair(7))
    THE_SCREEN.addstr(4, 2, "Section_:")
    THE_SCREEN.addstr(f" {OURSECTION}", curses.color_pair(7))
    THE_SCREEN.addstr(5, 2, "Battery_:")
    THE_SCREEN.addstr(f" {bool(BATTERYPOWER)}", curses.color_pair(7))

    THE_SCREEN.addstr(2, 25, "Multicast Group: ")
    THE_SCREEN.addstr(f"{MULTICAST_GROUP}", curses.color_pair(7))
    THE_SCREEN.addstr(3, 25, "Multicast Port_: ")
    THE_SCREEN.addstr(f"{MULTICAST_PORT}", curses.color_pair(7))
    THE_SCREEN.addstr(4, 25, "Interface IP___: ")
    THE_SCREEN.addstr(f"{INTERFACE_IP}", curses.color_pair(7))

    THE_SCREEN.addstr(2, 60, "Points_____: ")
    THE_SCREEN.addstr(f"{POINTS}", curses.color_pair(7))
    THE_SCREEN.addstr(3, 60, "Last Hour__: ")
    THE_SCREEN.addstr(f"{LASTHOUR}", curses.color_pair(7))
    THE_SCREEN.addstr(4, 60, "Last 15 Min: ")
    THE_SCREEN.addstr(f"{LAST15}", curses.color_pair(7))

    rectangle(THE_SCREEN, 6, 0, 23, 50)
    rectangle(THE_SCREEN, 6, 50, 16, 79)

    prectangle(THE_SCREEN, 16, 50, 23, 79)
    ptitle(THE_SCREEN, 6, 0, 50, "UDP Activity")
    ptitle(THE_SCREEN, 6, 50, 79, "Contacts")
    ptitle(THE_SCREEN, 16, 50, 79, "Operators")
    get_stats()
    THE_SCREEN.refresh()
    show_people()
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
                        json_data.get("date_and_time"),
                        json_data.get("frequency"),
                        json_data.get("band"),
                        json_data.get("mode"),
                        json_data.get("power"),
                        json_data.get("grid"),
                        json_data.get("opname"),
                        json_data.get("station"),
                    )
                )
                LOG.add_item(
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
                LOG.add_item(f"[{timestamp}] CONFIRM POST: {json_data.get('station')}")
                comm_log()
                get_stats()
                continue

            if json_data.get("cmd") == "LOG":
                LOG.add_item(f"[{timestamp}] GENERATE LOG: {json_data.get('station')}")
                cabrillo()
                packet = {"cmd": "RESPONSE"}
                packet["recipient"] = json_data.get("station")
                packet["subject"] = "LOG"
                bytes_to_send = bytes(dumps(packet), encoding="ascii")
                s.sendto(bytes_to_send, (MULTICAST_GROUP, MULTICAST_PORT))
                LOG.add_item(
                    f"[{timestamp}] GENERATE LOG CONF: {json_data.get('station')}"
                )
                continue

            if json_data.get("cmd") == "GET":
                LOG.add_item(f"[{timestamp}] {json_data}")
                comm_log()
                continue

            if json_data.get("cmd") == "DELETE":
                LOG.add_item(f"[{timestamp}] Deleting: {json_data.get('unique_id')}")
                DB.delete_contact(json_data.get("unique_id"))
                comm_log()
                packet = {"cmd": "RESPONSE"}
                packet["recipient"] = json_data.get("station")
                packet["subject"] = "DELETE"
                packet["unique_id"] = json_data.get("unique_id")
                bytes_to_send = bytes(dumps(packet), encoding="ascii")
                s.sendto(bytes_to_send, (MULTICAST_GROUP, MULTICAST_PORT))
                LOG.add_item(
                    f"[{timestamp}] CONFIRM DELETE: {json_data.get('station')}"
                )
                comm_log()
                get_stats()
                continue

            if json_data.get("cmd") == "UPDATE":
                LOG.add_item(
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
                LOG.add_item(
                    f"[{timestamp}] CONFIRM UPDATE: {json_data.get('station')}"
                )
                comm_log()
                get_stats()
                continue

            if json_data.get("cmd") == "PING":
                if json_data.get("station"):
                    band_mode = f"{json_data.get('band')} {json_data.get('mode')}"
                    if people.get(json_data.get("station")) != band_mode:
                        people[json_data.get("station")] = band_mode
                        LOG.add_item(
                            f"[{timestamp}] Band/Mode Change: {json_data.get('station')} "
                            f"{json_data.get('band')}M {json_data.get('mode')}"
                        )
                    show_people()
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
                LOG.add_item(f"[{timestamp}] GROUPQUERY: {json_data.get('station')}")
                comm_log()
                continue

            if json_data.get("cmd") == "CHAT":
                if "@stats" in json_data.get("message"):

                    bands = ["160", "80", "40", "20", "15", "10", "6", "2"]
                    blist = []
                    list_o_bands = DB.get_bands()
                    if list_o_bands:
                        for count in list_o_bands:
                            blist.append(count[0])

                    message = "\nBand   CW    PH    DI\n"
                    for band in bands:
                        cwt = DB.get_band_mode_tally(band, "CW")
                        dit = DB.get_band_mode_tally(band, "DI")
                        pht = DB.get_band_mode_tally(band, "PH")
                        line = (
                            f"{str(band).rjust(4, ' ')} "
                            f"{str(cwt[0]).rjust(5, ' ')} "
                            f"{str(pht[0]).rjust(5, ' ')} "
                            f"{str(dit[0]).rjust(5, ' ')}\n"
                        )
                        message += line

                    global QRP
                    (
                        cwcontacts,
                        phonecontacts,
                        digitalcontacts,
                        _,
                        last15,
                        lasthour,
                        _,
                        QRP,
                    ) = DB.stats()

                    points = (
                        (int(cwcontacts) * 2)
                        + (int(digitalcontacts) * 2)
                        + int(phonecontacts)
                    )

                    score = (((QRP * 3) * BATTERYPOWER) + 2) * points
                    message += (
                        f"\nScore {score}\n"
                        f"Last Hour {lasthour}\n"
                        f"Last 15 {last15}"
                    )
                    packet = {"cmd": "CHAT"}
                    packet["sender"] = "Server"
                    packet["message"] = message
                    bytes_to_send = bytes(dumps(packet), encoding="ascii")
                    try:
                        s.sendto(bytes_to_send, (MULTICAST_GROUP, int(MULTICAST_PORT)))
                    except OSError as err:
                        logging.debug("%s", err)

        except UnicodeDecodeError as err:
            print(f"[{timestamp}] Not JSON: {err}\n{payload}\n")
        except JSONDecodeError as err:
            print(f"[{timestamp}] Not JSON: {err}\n{payload}\n")


if args.log:
    cabrillo()
    curses.endwin()
    raise SystemExit(1)
wrapper(main)

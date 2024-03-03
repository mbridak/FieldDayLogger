#!/usr/bin/env python3
"""
K6GTE Field Day logger
Email: michael.bridak@gmail.com
https://github.com/mbridak/FieldDayLogger
GPL V3
"""
# pylint: disable=too-many-lines, invalid-name, no-member, no-value-for-parameter, line-too-long
# pylint: disable=logging-fstring-interpolation
# Nothing to see here move along.
# xplanet -body earth -window -longitude -117 -latitude 38
# -config Default -projection azmithal -radius 200 -wait 5


from math import radians, sin, cos, atan2, sqrt, asin, pi
from pathlib import Path
from datetime import datetime, timedelta
from json import dumps, loads, JSONDecodeError
from shutil import copyfile

# from xmlrpc.client import ServerProxy, Error
import struct
import datetime as dt
import os
import socket
import sys
import logging
import threading
import uuid
import queue
import time
from itertools import chain

import requests
from PyQt5.QtNetwork import QUdpSocket, QHostAddress
from PyQt5.QtGui import QFontDatabase
from PyQt5.QtCore import QDir, Qt
from PyQt5 import QtCore, QtGui, QtWidgets, uic

try:
    from fdlogger.lib.lookup import HamDBlookup, HamQTH, QRZlookup
    from fdlogger.lib.cat_interface import CAT
    from fdlogger.lib.settings import Settings
    from fdlogger.lib.database import DataBase
    from fdlogger.lib.cwinterface import CW
    from fdlogger.lib.n1mm import N1MM
    from fdlogger.lib.edit_opon import OpOn
    from fdlogger.lib.version import __version__
except ModuleNotFoundError:
    from lib.lookup import HamDBlookup, HamQTH, QRZlookup
    from lib.cat_interface import CAT
    from lib.settings import Settings
    from lib.database import DataBase
    from lib.cwinterface import CW
    from lib.n1mm import N1MM
    from lib.edit_opon import OpOn
    from lib.version import __version__


def load_fonts_from_dir(directory: str) -> set:
    """
    Well it loads fonts from a directory...
    """
    font_families = set()
    for _fi in QDir(directory).entryInfoList(["*.ttf", "*.woff", "*.woff2"]):
        _id = QFontDatabase.addApplicationFont(_fi.absoluteFilePath())
        font_families |= set(QFontDatabase.applicationFontFamilies(_id))
    return font_families


class QsoEdit(QtCore.QObject):
    """
    custom qt event signal used when qso is edited or deleted.
    """

    lineChanged = QtCore.pyqtSignal()


class MainWindow(QtWidgets.QMainWindow):
    """Main Window"""

    database = "FieldDay.db"
    power = "100"
    band = "40"
    mode = "CW"
    qrp = False
    highpower = False
    bandmodemult = 0
    cwcontacts = "0"
    phonecontacts = "0"
    digitalcontacts = "0"
    score = 0
    secPartial = {}
    secName = {}
    secState = {}
    scp = []
    wrkdsections = []
    linetopass = ""
    bands = ("160", "80", "60", "40", "20", "15", "10", "6", "2")
    cloudlogauthenticated = False
    qrzsession = False
    rigctrlsocket = ""
    rigonline = False
    markerfile = ".xplanet/markers/ham"
    usemarker = False
    oldfreq = 0
    oldmode = 0
    oldrfpower = 0
    basescore = 0
    powermult = 0
    datadict = {}
    dupdict = {}
    ft8dupe = ""
    fkeys = {}
    people = {}
    mygrid = None
    run_state = False
    groupcall = None
    server_commands = []
    server_seen = None
    opon_dialog = None

    def __init__(self, *args, **kwargs):
        """Initialize"""
        super().__init__(*args, **kwargs)
        self.working_path = os.path.dirname(__loader__.get_filename())
        data_path = self.working_path + "/data/main.ui"
        uic.loadUi(data_path, self)
        self.chat_window.hide()
        self.frame_5.show()
        self.frame_6.show()
        self.frame_7.show()
        self.frame_8.show()
        self.frame_9.show()
        self.group_call_indicator.hide()
        self.mycallEntry.show()
        self.db = DataBase(self.database)
        self.udp_fifo = queue.Queue()
        self.listWidget.itemDoubleClicked.connect(self.qsoclicked)
        self.callsign_entry.textEdited.connect(self.calltest)
        self.class_entry.textEdited.connect(self.classtest)
        self.section_entry.textEdited.connect(self.sectiontest)
        self.callsign_entry.returnPressed.connect(self.log_contact)
        self.chat_entry.returnPressed.connect(self.send_chat)
        self.class_entry.returnPressed.connect(self.log_contact)
        self.section_entry.returnPressed.connect(self.log_contact)
        self.mycallEntry.textEdited.connect(self.changemycall)
        self.myclassEntry.textEdited.connect(self.changemyclass)
        self.mysectionEntry.textEdited.connect(self.changemysection)
        self.band_selector.activated.connect(self.changeband)
        self.mode_selector.activated.connect(self.changemode)
        self.power_selector.valueChanged.connect(self.changepower)
        self.callsign_entry.editingFinished.connect(self.dup_check)
        self.section_entry.textEdited.connect(self.section_check)
        self.genLogButton.clicked.connect(self.generate_logs)
        self.run_button.clicked.connect(self.run_button_pressed)
        icon_path = self.working_path + "/icon/"
        self.radio_grey = QtGui.QPixmap(icon_path + "radio_grey.png")
        self.radio_red = QtGui.QPixmap(icon_path + "radio_red.png")
        self.radio_green = QtGui.QPixmap(icon_path + "radio_green.png")
        self.cloud_grey = QtGui.QPixmap(icon_path + "cloud_grey.png")
        self.cloud_red = QtGui.QPixmap(icon_path + "cloud_red.png")
        self.cloud_green = QtGui.QPixmap(icon_path + "cloud_green.png")
        self.radio_icon.setPixmap(self.radio_grey)
        self.cloudlog_icon.setPixmap(self.cloud_grey)
        self.callbook_icon.setStyleSheet("color: rgb(136, 138, 133);")
        self.settingsbutton.clicked.connect(self.settings_pressed)
        self.F1.clicked.connect(self.sendf1)
        self.F2.clicked.connect(self.sendf2)
        self.F3.clicked.connect(self.sendf3)
        self.F4.clicked.connect(self.sendf4)
        self.F5.clicked.connect(self.sendf5)
        self.F6.clicked.connect(self.sendf6)
        self.F7.clicked.connect(self.sendf7)
        self.F8.clicked.connect(self.sendf8)
        self.F9.clicked.connect(self.sendf9)
        self.F10.clicked.connect(self.sendf10)
        self.F11.clicked.connect(self.sendf11)
        self.F12.clicked.connect(self.sendf12)
        self.fakefreqs = {
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
            "6": ["50030", "50300", "50125"],
            "2": ["144030", "144144", "144250"],
            "222": ["222100", "222070", "222100"],
            "432": ["432070", "432200", "432100"],
            "SAT": ["144144", "144144", "144144"],
        }
        self.contactlookup = {
            "call": "",
            "grid": "",
            "bearing": "",
            "name": "",
            "nickname": "",
            "error": "",
            "distance": "",
        }
        self.preference = {
            "mycall": "",
            "myclass": "",
            "mysection": "",
            "power": "0",
            "altpower": 0,
            "usehamdb": 0,
            "useqrz": 0,
            "usehamqth": 0,
            "lookupusername": "w1aw",
            "lookuppassword": "secret",
            "userigctld": 0,
            "useflrig": 0,
            "CAT_ip": "localhost",
            "CAT_port": 12345,
            "cloudlog": 0,
            "cloudlogapi": "c01234567890123456789",
            "cloudlogurl": "https://www.cloudlog.com/Cloudlog/index.php/api/",
            "cloudlogstationid": "",
            "usemarker": 0,
            "markerfile": ".xplanet/markers/ham",
            "cwtype": 0,
            "cwip": "localhost",
            "cwport": 6789,
            "useserver": 0,
            "multicast_group": "239.1.1.1",
            "multicast_port": 2239,
            "interface_ip": "0.0.0.0",
            "send_n1mm_packets": 0,
            "n1mm_station_name": "20M CW Tent",
            "n1mm_operator": "Bernie",
            "n1mm_ip": "127.0.0.1",
            "n1mm_radioport": 12060,
            "n1mm_contactport": 12061,
            "n1mm_lookupport": 12060,
            "n1mm_scoreport": 12062,
        }
        self.reference_preference = self.preference.copy()
        self.look_up = None
        self.cat_control = None
        self.cw = None
        self.connect_to_server = False
        self.multicast_group = None
        self.multicast_port = None
        self.interface_ip = None
        self._udpwatch = None
        self.readpreferences()
        self.radiochecktimer = QtCore.QTimer()
        self.radiochecktimer.timeout.connect(self.poll_radio)
        self.radiochecktimer.start(1000)
        self.ft8dupechecktimer = QtCore.QTimer()
        self.ft8dupechecktimer.timeout.connect(self.ft8dupecheck)
        self.ft8dupechecktimer.start(1000)

        # ft8 udp server
        self.udp_socket = QUdpSocket()
        self.udp_socket.bind(QHostAddress.LocalHost, 2237)
        self.udp_socket.readyRead.connect(self.on_udp_socket_ready_read)

    def get_opon(self) -> None:
        """
        Ctrl+O Open the OPON dialog.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        self.opon_dialog = OpOn(os.path.dirname(__loader__.get_filename()))
        self.opon_dialog.accepted.connect(self.new_op)
        self.opon_dialog.open()

    def new_op(self) -> None:
        """
        Called when the user clicks the OK button on the OPON dialog.
        Create the new directory and copy the phonetic files.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """

        if self.opon_dialog.NewOperator.text():
            newop = self.opon_dialog.NewOperator.text().upper()
            if newop:
                self.n1mm.set_operator(newop)
                self.preference["mycall"] = newop
                self.preference["n1mm_operator"] = newop
                logger.debug(f"{newop=}")
                self.writepreferences()
        self.opon_dialog.close()

        # self.make_op_dir()

    def show_people(self):
        """Display operators"""
        rev_dict = {}
        for key, value in self.people.items():
            rev_dict.setdefault(value, set()).add(key)
        result = set(
            chain.from_iterable(
                values for key, values in rev_dict.items() if len(values) > 1
            )
        )
        self.users_list.clear()
        self.users_list.insertPlainText("Operators\n")
        for op_callsign in self.people:
            if op_callsign in result:
                self.users_list.setTextColor(QtGui.QColor(245, 121, 0))
                self.users_list.insertPlainText(
                    f"{op_callsign.rjust(6,' ')} {self.people.get(op_callsign).rjust(6, ' ')}\n"
                )
                self.users_list.setTextColor(QtGui.QColor(211, 215, 207))
            else:
                self.users_list.insertPlainText(
                    f"{op_callsign.rjust(6,' ')} {self.people.get(op_callsign).rjust(6, ' ')}\n"
                )

    def show_dirty_records(self):
        """Checks for dirty records, Changes Generate Log button to give visual indication."""
        if self.connect_to_server:
            result = self.db.count_all_dirty_contacts()
            all_dirty_count = result.get("alldirty")
            if all_dirty_count:
                self.genLogButton.setStyleSheet("background-color: red;")
                self.genLogButton.setText(f"UnVfyd: {all_dirty_count}")
            else:
                self.genLogButton.setStyleSheet("background-color: rgb(92, 53, 102);")
                self.genLogButton.setText("Generate Logs")
        else:
            self.genLogButton.setStyleSheet("background-color: rgb(92, 53, 102);")
            self.genLogButton.setText("Generate Logs")

    def resolve_dirty_records(self):
        """Go through dirty records and submit them to the server."""
        if self.connect_to_server:
            records = self.db.fetch_all_dirty_contacts()
            self.infobox.setTextColor(QtGui.QColor(211, 215, 207))
            self.infobox.insertPlainText(f"Resolving {len(records)} unsent contacts.\n")
            app.processEvents()
            if records:
                for count, dirty_contact in enumerate(records):
                    contact = {}
                    contact["cmd"] = "POST"
                    contact["station"] = self.preference.get("mycall")
                    stale = datetime.now() + timedelta(seconds=30)
                    contact["expire"] = stale.isoformat()
                    contact["unique_id"] = dirty_contact.get("unique_id")
                    contact["hiscall"] = dirty_contact.get("callsign")
                    contact["class"] = dirty_contact.get("class")
                    contact["section"] = dirty_contact.get("section")
                    contact["date_and_time"] = dirty_contact.get("date_time")
                    contact["frequency"] = dirty_contact.get("frequency")
                    contact["band"] = dirty_contact.get("band")
                    contact["mode"] = dirty_contact.get("mode")
                    contact["power"] = dirty_contact.get("power")
                    contact["grid"] = dirty_contact.get("grid")
                    contact["opname"] = dirty_contact.get("opname")
                    self.server_commands.append(contact)
                    bytesToSend = bytes(dumps(contact), encoding="ascii")
                    try:
                        self.server_udp.sendto(
                            bytesToSend,
                            (self.multicast_group, int(self.multicast_port)),
                        )
                    except OSError as err:
                        logger.warning("%s", err)
                    time.sleep(0.1)  # Do I need this?
                    self.infoline.setText(f"Sending {count}\n")
                    app.processEvents()

    def clear_dirty_flag(self, unique_id):
        """clear the dirty flag on record once response is returned from server."""
        self.db.clear_dirty_flag(unique_id)
        self.show_dirty_records()

    def remove_confirmed_commands(self, data):
        """Removed confirmed commands from the sent commands list."""
        for index, item in enumerate(self.server_commands):
            if item.get("unique_id") == data.get("unique_id") and item.get(
                "cmd"
            ) == data.get("subject"):
                self.server_commands.pop(index)
                self.clear_dirty_flag(data.get("unique_id"))
                self.infoline.setText(f"Confirmed {data.get('subject')}")

    def check_for_stale_commands(self):
        """
        Check through server commands to see if there has not been a reply in 30 seconds.
        Resubmits those that are stale.
        """
        if self.connect_to_server:
            for index, item in enumerate(self.server_commands):
                expired = datetime.strptime(item.get("expire"), "%Y-%m-%dT%H:%M:%S.%f")
                if datetime.now() > expired:
                    newexpire = datetime.now() + timedelta(seconds=30)
                    self.server_commands[index]["expire"] = newexpire.isoformat()
                    bytesToSend = bytes(dumps(item), encoding="ascii")
                    try:
                        self.server_udp.sendto(
                            bytesToSend,
                            (self.multicast_group, int(self.multicast_port)),
                        )
                    except OSError as err:
                        logger.warning("%s", err)

    def send_chat(self):
        """Sends UDP chat packet with text entered in chat_entry field."""
        message = self.chat_entry.text()
        packet = {"cmd": "CHAT"}
        packet["sender"] = self.preference.get("mycall", "")
        packet["message"] = message
        bytesToSend = bytes(dumps(packet), encoding="ascii")
        try:
            self.server_udp.sendto(
                bytesToSend, (self.multicast_group, int(self.multicast_port))
            )
        except OSError as err:
            logger.warning("%s", err)
        self.chat_entry.setText("")

    def display_chat(self, sender, body):
        """Displays the chat history."""
        if self.preference.get("mycall") in body.upper():
            self.chatlog.setTextColor(QtGui.QColor(245, 121, 0))
        self.chatlog.insertPlainText(f"\n{sender}: {body}")
        self.chatlog.setTextColor(QtGui.QColor(211, 215, 207))
        self.chatlog.ensureCursorVisible()

    def watch_udp(self):
        """Puts UDP datagrams in a FIFO queue"""
        while True:
            if self.connect_to_server:
                try:
                    datagram = self.server_udp.recv(1500)
                except socket.timeout:
                    time.sleep(1)
                    continue
                if datagram:
                    self.udp_fifo.put(datagram)
            else:
                time.sleep(1)

    def check_udp_queue(self):
        """checks the UDP datagram queue."""
        if self.server_seen:
            if datetime.now() > self.server_seen:
                self.group_call_indicator.setStyleSheet(
                    "border: 1px solid green;\nbackground-color: red;\ncolor: yellow;"
                )
        while not self.udp_fifo.empty():
            datagram = self.udp_fifo.get()
            try:
                json_data = loads(datagram.decode())
            except UnicodeDecodeError as err:
                the_error = f"Not Unicode: {err}\n{datagram}"
                logger.info(the_error)
                continue
            except JSONDecodeError as err:
                the_error = f"Not JSON: {err}\n{datagram}"
                logger.info(the_error)
                continue
            logger.info("%s", json_data)

            if json_data.get("cmd") == "PING":
                if json_data.get("station"):
                    band_mode = f"{json_data.get('band')} {json_data.get('mode')}"
                    if self.people.get(json_data.get("station")) != band_mode:
                        self.people[json_data.get("station")] = band_mode
                    self.show_people()
                if json_data.get("host"):
                    self.server_seen = datetime.now() + timedelta(seconds=30)
                    self.group_call_indicator.setStyleSheet("border: 1px solid green;")
                continue

            if json_data.get("cmd") == "RESPONSE":
                if json_data.get("recipient") == self.preference.get("mycall"):
                    if json_data.get("subject") == "HOSTINFO":
                        self.groupcall = json_data.get("groupcall", "")
                        self.myclassEntry.setText(str(json_data.get("groupclass", "")))
                        self.mysectionEntry.setText(
                            str(json_data.get("groupsection", ""))
                        )
                        self.group_call_indicator.setText(self.groupcall.center(14))
                        self.changemyclass()
                        self.changemysection()
                        self.mycallEntry.hide()
                        self.server_seen = datetime.now() + timedelta(seconds=30)
                        self.group_call_indicator.setStyleSheet(
                            "border: 1px solid green;"
                        )
                        return
                    if json_data.get("subject") == "LOG":
                        self.infoline.setText("Server Generated Log.")

                    if json_data.get("subject") == "DUPE":
                        if json_data.get("isdupe") != 0:
                            if json_data.get("contact") == self.callsign_entry.text():
                                self.flash()
                                self.infobox.setTextColor(QtGui.QColor(245, 121, 0))
                                self.infobox.insertPlainText(
                                    f"{json_data.get('contact')}: " "Server DUPE\n"
                                )

                    self.remove_confirmed_commands(json_data)
                    continue

            if json_data.get("cmd") == "CHAT":
                self.display_chat(json_data.get("sender"), json_data.get("message"))
                continue

            if json_data.get("cmd") == "GROUPQUERY":
                if self.groupcall:
                    self.send_status_udp()

    def query_group(self):
        """Sends request to server asking for group call/class/section."""
        update = {
            "cmd": "GROUPQUERY",
            "station": self.preference.get("mycall", ""),
        }
        bytesToSend = bytes(dumps(update), encoding="ascii")
        try:
            self.server_udp.sendto(
                bytesToSend, (self.multicast_group, int(self.multicast_port))
            )
        except OSError as err:
            logger.warning("%s", err)

    def check_dupe_status_udp(self):
        """Ask server if our contact is a dupe"""
        if self.connect_to_server:
            if self.groupcall is None and self.preference["mycall"] != "":
                self.query_group()
                return

            ask_if_dupe = {
                "cmd": "DUPE",
                "mode": self.mode,
                "band": self.band,
                "station": self.preference["mycall"],
                "contact": self.callsign_entry.text(),
            }
            bytesToSend = bytes(dumps(ask_if_dupe), encoding="ascii")
            try:
                self.server_udp.sendto(
                    bytesToSend, (self.multicast_group, int(self.multicast_port))
                )
            except OSError as err:
                logger.warning("%s", err)

            self.check_for_stale_commands()

    def send_status_udp(self):
        """Send status update to server informing of our band and mode"""
        if self.connect_to_server:
            if self.groupcall is None and self.preference["mycall"] != "":
                self.query_group()
                return

            update = {
                "cmd": "PING",
                "mode": self.mode,
                "band": self.band,
                "station": self.preference["mycall"],
            }
            bytesToSend = bytes(dumps(update), encoding="ascii")
            try:
                self.server_udp.sendto(
                    bytesToSend, (self.multicast_group, int(self.multicast_port))
                )
            except OSError as err:
                logger.warning("%s", err)

            self.check_for_stale_commands()

    def clearcontactlookup(self):
        """clearout the contact lookup"""
        self.contactlookup["call"] = ""
        self.contactlookup["grid"] = ""
        self.contactlookup["name"] = ""
        self.contactlookup["nickname"] = ""
        self.contactlookup["error"] = ""
        self.contactlookup["distance"] = ""
        self.contactlookup["bearing"] = ""

    def lazy_lookup(self, acall: str):
        """El Lookup De Lazy"""
        if self.look_up:
            if acall == self.contactlookup["call"]:
                return

            self.contactlookup["call"] = acall
            (
                self.contactlookup["grid"],
                self.contactlookup["name"],
                self.contactlookup["nickname"],
                self.contactlookup["error"],
            ) = self.look_up.lookup(acall)
            if self.contactlookup["grid"] and self.mygrid:
                self.contactlookup["distance"] = self.distance(
                    self.mygrid, self.contactlookup["grid"]
                )
                self.contactlookup["bearing"] = self.bearing(
                    self.mygrid, self.contactlookup["grid"]
                )
            logger.info("%s", self.contactlookup)
            self.infoline.setText(
                f"{self.contactlookup.get('nickname') if self.contactlookup.get('nickname') else self.contactlookup.get('name')}"
                f" {self.contactlookup.get('grid')}"
            )

    def distance(self, grid1: str, grid2: str) -> float:
        """
        Takes two maidenhead gridsquares and returns the distance between the two in kilometers.
        """
        lat1, lon1 = self.gridtolatlon(grid1)
        lat2, lon2 = self.gridtolatlon(grid2)
        return round(self.haversine(lon1, lat1, lon2, lat2))

    def bearing(self, grid1: str, grid2: str) -> float:
        """calculate bearing to contact"""
        lat1, lon1 = self.gridtolatlon(grid1)
        lat2, lon2 = self.gridtolatlon(grid2)
        lat1 = radians(lat1)
        lon1 = radians(lon1)
        lat2 = radians(lat2)
        lon2 = radians(lon2)
        londelta = lon2 - lon1
        why = sin(londelta) * cos(lat2)
        exs = cos(lat1) * sin(lat2) - sin(lat1) * cos(lat2) * cos(londelta)
        brng = atan2(why, exs)
        brng *= 180 / pi

        if brng < 0:
            brng += 360

        return round(brng)

    @staticmethod
    def haversine(lon1, lat1, lon2, lat2):
        """
        Calculate the great circle distance in kilometers between two points
        on the earth (specified in decimal degrees)
        """
        # convert degrees to radians
        lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])

        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        aye = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        cee = 2 * asin(sqrt(aye))
        arrgh = 6372.8  # Radius of earth in kilometers.
        return cee * arrgh

    @staticmethod
    def getint(bytestring):
        """
        Returns an int from a bigendian signed 4 byte string
        """
        return int.from_bytes(bytestring, byteorder="big", signed=True)

    @staticmethod
    def getuint(bytestring):
        """
        Returns an int from a bigendian unsigned 4 byte string
        """
        return int.from_bytes(bytestring, byteorder="big", signed=False)

    @staticmethod
    def getbool(bytestring):
        """
        Returns a bool from a 1 byte string
        """
        return bool.from_bytes(bytestring, byteorder="big", signed=False)

    def getvalue(self, item):
        """I don't remember what this does."""
        if item in self.datadict:
            return self.datadict[item]
        return "NOT_FOUND"

    def update_time(self):
        """updates the time"""
        now = datetime.now().isoformat(" ")[5:19].replace("-", "/")
        utcnow = datetime.now(dt.timezone.utc).isoformat(" ")[5:19].replace("-", "/")
        self.localtime.setText(now)
        self.utctime.setText(utcnow)

    def on_udp_socket_ready_read(self):
        """
        This will process incomming UDP log packets from WSJT-X.
        I Hope...
        """
        self.datadict = {}
        datagram, sender_host, sender_port_number = self.udp_socket.readDatagram(
            self.udp_socket.pendingDatagramSize()
        )
        logger.info("%s %s %s", sender_host, sender_port_number, datagram)

        if datagram[0:4] != b"\xad\xbc\xcb\xda":
            return  # bail if no wsjt-x magic number
        version = self.getuint(datagram[4:8])
        packettype = self.getuint(datagram[8:12])
        uniquesize = self.getint(datagram[12:16])
        unique = datagram[16 : 16 + uniquesize].decode()
        payload = datagram[16 + uniquesize :]

        if packettype == 0:  # Heartbeat
            hbmaxschema = self.getuint(payload[0:4])
            hbversion_len = self.getint(payload[4:8])
            hbversion = payload[8 : 8 + hbversion_len].decode()
            print(
                f"heartbeat: sv:{version} p:{packettype} "
                f"u:{unique}: ms:{hbmaxschema} av:{hbversion}"
            )
            return

        if packettype == 1:  # Status
            [dialfreq] = struct.unpack(">Q", payload[0:8])
            modelen = self.getint(payload[8:12])
            mode = payload[12 : 12 + modelen].decode()
            payload = payload[12 + modelen :]
            dxcalllen = self.getint(payload[0:4])
            dxcall = payload[4 : 4 + dxcalllen].decode()
            logger.info(
                "Status: sv:%s p:%s u:%s df:%s m:%s dxc:%s",
                version,
                packettype,
                unique,
                dialfreq,
                mode,
                dxcall,
            )

            if f"{dxcall}{self.band}{self.mode}" in self.dupdict:
                self.ft8dupe = f"{dxcall} {self.band}M {self.mode} FT8 Dupe!"
            return

        if packettype == 2:  # Decode commented out because we really don't care
            return

        if packettype != 12:
            return  # bail if not logged ADIF
        # if log packet it will contain this nugget.
        gotcall = datagram.find(b"<call:")
        if gotcall != -1:
            datagram = datagram[gotcall:]  # strip everything else
        else:
            return  # Otherwise we don't want to bother with this packet

        data = datagram.decode()
        splitdata = data.upper().split("<")

        for data in splitdata:
            if data:
                tag = data.split(":")
                if tag == ["EOR>"]:
                    break
                self.datadict[tag[0]] = tag[1].split(">")[1].strip()

        contest_id = self.getvalue("CONTEST_ID")
        if contest_id == "ARRL-FIELD-DAY":
            call = self.getvalue("CALL")
            dayt = self.getvalue("QSO_DATE")
            tyme = self.getvalue("TIME_ON")
            the_dt = f"{dayt[0:4]}-{dayt[4:6]}-{dayt[6:8]} {tyme[0:2]}:{tyme[2:4]}:{tyme[4:6]}"
            freq = int(float(self.getvalue("FREQ")) * 1000000)
            band = self.getvalue("BAND").split("M")[0]
            grid = self.getvalue("GRIDSQUARE")
            name = self.getvalue("NAME")
            if grid == "NOT_FOUND" or name == "NOT_FOUND":
                if grid == "NOT_FOUND":
                    grid = ""
                if name == "NOT_FOUND":
                    name = ""
                if self.look_up:
                    grid, name, _, _ = self.look_up.lookup(call)
            hisclass, hissect = self.getvalue("SRX_STRING").split(" ")
            # power = int(float(self.getvalue("TX_PWR")))
            contact = (
                call,
                hisclass,
                hissect,
                the_dt,
                freq,
                band,
                "DI",
                self.preference["power"],
                grid,
                name,
            )
            self.db.log_contact(contact)
            self.sections()
            self.stats()
            self.updatemarker()
            self.logwindow()
            self.clearinputs()
            self.postcloudlog()

    def ft8dupecheck(self):
        """Dup Check"""
        if self.ft8dupe != "":
            self.infobox.clear()
            self.flash()
            self.infobox.setTextColor(QtGui.QColor(245, 121, 0))
            self.infobox.insertPlainText(f"{self.ft8dupe}\n")
        else:
            self.infobox.setTextColor(QtGui.QColor(211, 215, 207))
        self.ft8dupe = ""

    def run_button_pressed(self):
        """The run/S&P button was pressed."""
        if self.run_button.text() == "Run":
            self.run_state = False
            self.run_button.setText("SP")
        else:
            self.run_state = True
            self.run_button.setText("Run")
        self.read_cw_macros()

    def read_cw_macros(self):
        """
        Reads in the CW macros, firsts it checks to see if the file exists. If it does not,
        and this has been packaged with pyinstaller it will copy the default file from the
        temp directory this is running from... In theory.
        """

        if not Path("./cwmacros_fd.txt").exists():
            logger.info("read_cw_macros: copying default macro file.")
            data_path = self.working_path + "/data/cwmacros_fd.txt"
            copyfile(data_path, "./cwmacros_fd.txt")
        with open("./cwmacros_fd.txt", "r", encoding="utf-8") as file_descriptor:
            for line in file_descriptor:
                try:
                    mode, fkey, buttonname, cwtext = line.split("|")
                    if mode.strip().upper() == "R" and self.run_state:
                        self.fkeys[fkey.strip()] = (buttonname.strip(), cwtext.strip())
                    if mode.strip().upper() != "R" and not self.run_state:
                        self.fkeys[fkey.strip()] = (buttonname.strip(), cwtext.strip())
                except ValueError as err:
                    logger.info("read_cw_macros: %s", err)
        fkeys_keys = self.fkeys.keys()
        if "F1" in fkeys_keys:
            self.F1.setText(f"F1: {self.fkeys['F1'][0]}")
            self.F1.setToolTip(self.fkeys["F1"][1])
        if "F2" in fkeys_keys:
            self.F2.setText(f"F2: {self.fkeys['F2'][0]}")
            self.F2.setToolTip(self.fkeys["F2"][1])
        if "F3" in fkeys_keys:
            self.F3.setText(f"F3: {self.fkeys['F3'][0]}")
            self.F3.setToolTip(self.fkeys["F3"][1])
        if "F4" in fkeys_keys:
            self.F4.setText(f"F4: {self.fkeys['F4'][0]}")
            self.F4.setToolTip(self.fkeys["F4"][1])
        if "F5" in fkeys_keys:
            self.F5.setText(f"F5: {self.fkeys['F5'][0]}")
            self.F5.setToolTip(self.fkeys["F5"][1])
        if "F6" in fkeys_keys:
            self.F6.setText(f"F6: {self.fkeys['F6'][0]}")
            self.F6.setToolTip(self.fkeys["F6"][1])
        if "F7" in fkeys_keys:
            self.F7.setText(f"F7: {self.fkeys['F7'][0]}")
            self.F7.setToolTip(self.fkeys["F7"][1])
        if "F8" in fkeys_keys:
            self.F8.setText(f"F8: {self.fkeys['F8'][0]}")
            self.F8.setToolTip(self.fkeys["F8"][1])
        if "F9" in fkeys_keys:
            self.F9.setText(f"F9: {self.fkeys['F9'][0]}")
            self.F9.setToolTip(self.fkeys["F9"][1])
        if "F10" in fkeys_keys:
            self.F10.setText(f"F10: {self.fkeys['F10'][0]}")
            self.F10.setToolTip(self.fkeys["F10"][1])
        if "F11" in fkeys_keys:
            self.F11.setText(f"F11: {self.fkeys['F11'][0]}")
            self.F11.setToolTip(self.fkeys["F11"][1])
        if "F12" in fkeys_keys:
            self.F12.setText(f"F12: {self.fkeys['F12'][0]}")
            self.F12.setToolTip(self.fkeys["F12"][1])

    def process_macro(self, macro):
        """process string substitutions"""
        macro = macro.upper()
        if self.groupcall and self.connect_to_server:
            macro = macro.replace("{MYCALL}", self.groupcall)
        else:
            macro = macro.replace("{MYCALL}", self.preference["mycall"])
        macro = macro.replace("{MYCLASS}", self.preference["myclass"])
        macro = macro.replace("{MYSECT}", self.preference["mysection"])
        macro = macro.replace("{HISCALL}", self.callsign_entry.text())
        return macro

    def settings_pressed(self):
        """Do this after Settings icon clicked."""
        settingsdialog = Settings(self)
        settingsdialog.exec()
        self.infobox.clear()
        self.look_up = None
        self.cat_control = None
        self.readpreferences()
        if self.preference["useqrz"]:
            self.look_up = QRZlookup(
                self.preference["lookupusername"], self.preference["lookuppassword"]
            )
        if self.preference["usehamdb"]:
            self.look_up = HamDBlookup()
        if self.preference["usehamqth"]:
            self.look_up = HamQTH(
                self.preference["lookupusername"],
                self.preference["lookuppassword"],
            )
        if self.preference["useflrig"]:
            self.cat_control = CAT(
                "flrig", self.preference["CAT_ip"], self.preference["CAT_port"]
            )
        if self.preference["userigctld"]:
            self.cat_control = CAT(
                "rigctld", self.preference["CAT_ip"], self.preference["CAT_port"]
            )

        if self.preference["cloudlog"]:
            cloudlogapi = self.preference["cloudlogapi"]
            cloudlogurl = self.preference["cloudlogurl"]

            payload = "/validate/key=" + cloudlogapi
            logger.info("%s", cloudlogurl + payload)
            try:
                result = requests.get(cloudlogurl + payload, timeout=2.0)
                self.cloudlogauthenticated = False
                if result.status_code == 200 or result.status_code == 400:
                    self.cloudlogauthenticated = True
            except requests.exceptions.ConnectionError as exception:
                logger.warning("cloudlog authentication: %s", exception)

    @staticmethod
    def has_internet():
        """pings external dns server to check internet"""
        try:
            socket.create_connection(("1.1.1.1", 53))
            return True
        except OSError:
            return False

    def cloudlogauth(self):
        """Check if cloudlog is happy with us."""
        self.cloudlog_icon.setPixmap(self.cloud_grey)
        self.cloudlogauthenticated = False
        if self.preference["cloudlog"]:
            try:
                self.cloudlog_icon.setPixmap(self.cloud_red)
                test = (
                    self.preference["cloudlogurl"]
                    + "auth/"
                    + self.preference["cloudlogapi"]
                )
                logger.debug("%s", test)
                result = requests.get(test, params={}, timeout=2.0)
                if result.status_code == 200 and result.text.find("<status>") > 0:
                    if (
                        result.text[
                            result.text.find("<status>")
                            + 8 : result.text.find("</status>")
                        ]
                        == "Valid"
                    ):
                        self.cloudlogauthenticated = True
                        self.cloudlog_icon.setPixmap(self.cloud_green)
                        logger.info("Cloudlog: Authenticated.")
                else:
                    logger.warning(
                        "Cloudlog: %s Unable to authenticate.", result.status_code
                    )
            except requests.exceptions.RequestException as exception:
                self.infobox.insertPlainText(
                    f"****Cloudlog Auth Error:****\n{exception}\n"
                )
                logger.warning("Cloudlog: %s", exception)

    def set_fakefreq(self, newfreq):
        """doc"""
        if self.getband(str(newfreq)) != "0":
            modes = {"CW": 0, "DI": 1, "PH": 2, "FT8": 1, "SSB": 2}
            self.fakefreqs[self.getband(str(newfreq))][modes[self.mode]] = str(
                newfreq / 1000
            )
            self.setband(str(self.getband(str(newfreq))))

    def fakefreq(self, band, mode):
        """
        If unable to obtain a frequency from the rig,
        This will return a sane value for a frequency mainly for the cabrillo and adif log.
        Takes a band and mode as input and returns freq in khz.
        """
        logger.info("fakefreq: band:%s mode:%s", band, mode)
        modes = {"CW": 0, "DI": 1, "PH": 2, "FT8": 1, "SSB": 2}
        if not band:
            return 0
        freqtoreturn = self.fakefreqs[band][modes[mode]]
        logger.info("fakefreq: returning:%s", freqtoreturn)
        return freqtoreturn

    @staticmethod
    def getband(freq):
        """
        Takes a frequency in hz and returns the band.
        """
        if freq.isnumeric():
            frequency = int(float(freq))
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

    @staticmethod
    def getmode(rigmode):
        """
        Takes the mode returned from the radio and returns a normalized value,
        CW for CW, PH for voice, DI for digital
        """
        if rigmode in ("CW", "CWR"):
            return "CW"
        if rigmode in ("USB", "LSB", "FM", "AM"):
            return "PH"
        return "DI"  # All else digital

    def setband(self, theband):
        """
        Takes a band in meters and programatically changes the onscreen dropdown to match.
        """
        self.band_selector.setCurrentIndex(self.band_selector.findText(theband))
        self.changeband()

    def setmode(self, themode):
        """
        Takes a string for the mode (CW, PH, DI) and programatically changes the onscreen dropdown.
        """
        self.mode_selector.setCurrentIndex(self.mode_selector.findText(themode))
        self.changemode()

    def poll_radio(self):
        """poll radios"""
        if self.cat_control:
            newfreq = self.cat_control.get_vfo()
            newmode = self.cat_control.get_mode()
            if newfreq == "" or newmode == "":
                self.radio_icon.setPixmap(self.radio_red)
                return
            self.radio_icon.setPixmap(self.radio_green)
            if newfreq != self.oldfreq or newmode != self.oldmode:
                self.oldfreq = newfreq
                self.set_fakefreq(int(newfreq))
                self.oldmode = newmode
                if self.getband(newfreq) == 0:
                    self.setband(str(self.getband(self.oldfreq)))
                else:
                    self.setband(str(self.getband(newfreq)))
                self.setmode(str(self.getmode(newmode)))
                self.radio_icon.setPixmap(self.radio_green)
            if self.preference.get("send_n1mm_packets"):
                self.n1mm.radio_info["StationName"] = self.preference.get(
                    "n1mm_station_name", ""
                )
                self.n1mm.radio_info["Freq"] = newfreq[:-1]
                self.n1mm.radio_info["TXFreq"] = newfreq[:-1]
                self.n1mm.radio_info["Mode"] = newmode
                self.n1mm.radio_info["OpCall"] = self.preference.get("mycallsign", "")
                self.n1mm.radio_info["IsRunning"] = str(self.run_state)
                if self.cat_control.get_ptt() == "0":
                    self.n1mm.radio_info["IsTransmitting"] = "False"
                else:
                    self.n1mm.radio_info["IsTransmitting"] = "True"
                self.n1mm.send_radio()
        else:
            logger.info("cat_control %s", self.cat_control)
            self.radio_icon.setPixmap(QtGui.QPixmap(self.radio_grey))
            self.oldmode = (
                self.mode
            )  # Set so the UDP packet sends mode when no radio connected - NY4I

    def flash(self):
        """Flash the screen"""
        self.setStyleSheet(
            "background-color: rgb(245, 121, 0);\ncolor: rgb(211, 215, 207);"
        )
        app.processEvents()
        self.setStyleSheet(
            "background-color: rgb(42, 42, 42);\ncolor: rgb(211, 215, 207);"
        )
        app.processEvents()

    def keyPressEvent(self, event):  # pylint: disable=invalid-name
        """This extends QT's KeyPressEvent, handle tab, esc and function keys"""
        event_key = event.key()
        if event_key == Qt.Key_Escape:
            self.clearinputs()
            self.clearcontactlookup()
            if self.cw is not None:
                if self.cw.servertype == 1:
                    self.cw.speed += 1
                    self.cw.sendcw("\x1b4")
                    self.infoline.setText("")
            return
        if event_key == Qt.Key.Key_PageUp:
            if self.cw is not None:
                if self.cw.servertype == 1:
                    self.cw.speed += 1
                    self.cw.sendcw(f"\x1b2{self.cw.speed}")
                    self.infoline.setText(f"CW speed set to {self.cw.speed}")
        if event_key == Qt.Key.Key_PageDown:
            if self.cw is not None:
                if self.cw.servertype == 1:
                    self.cw.speed -= 1
                    self.cw.sendcw(f"\x1b2{self.cw.speed}")
                    self.infoline.setText(f"CW speed set to {self.cw.speed}")
        if event_key == Qt.Key_Tab:
            if self.section_entry.hasFocus():
                logger.info("From section")
                self.callsign_entry.setFocus()
                self.callsign_entry.deselect()
                self.callsign_entry.end(False)
                return
            if self.class_entry.hasFocus():
                logger.info("From class")
                self.section_entry.setFocus()
                self.section_entry.deselect()
                self.section_entry.end(False)
                return
            if self.callsign_entry.hasFocus():
                logger.info("From callsign")
                _thethread = threading.Thread(
                    target=self.lazy_lookup,
                    args=(self.callsign_entry.text(),),
                    daemon=True,
                )
                _thethread.start()
                self.class_entry.setFocus()
                self.class_entry.deselect()
                self.class_entry.end(False)
                return
        if event_key == Qt.Key_F1:
            self.sendf1()
            return
        if event_key == Qt.Key_F2:
            self.sendf2()
            return
        if event_key == Qt.Key_F3:
            self.sendf3()
            return
        if event_key == Qt.Key_F4:
            self.sendf4()
            return
        if event_key == Qt.Key_F5:
            self.sendf5()
            return
        if event_key == Qt.Key_F6:
            self.sendf6()
            return
        if event_key == Qt.Key_F7:
            self.sendf7()
            return
        if event_key == Qt.Key_F8:
            self.sendf8()
            return
        if event_key == Qt.Key_F9:
            self.sendf9()
            return
        if event_key == Qt.Key_F10:
            self.sendf10()
            return
        if event_key == Qt.Key_F11:
            self.sendf11()
            return
        if event_key == Qt.Key_F12:
            self.sendf12()

    def sendf1(self):
        """send f1"""
        if self.cw is not None:
            self.infoline.setText(f"Sending {self.process_macro(self.F1.toolTip())}")
            if self.preference.get("send_n1mm_packets"):
                self.n1mm.radio_info["FunctionKeyCaption"] = self.F1.text()
            self.cw.sendcw(f"{self.process_macro(self.F1.toolTip())} ")

    def sendf2(self):
        """send f2"""
        if self.cw is not None:
            self.infoline.setText(f"Sending {self.process_macro(self.F2.toolTip())}")
            if self.preference.get("send_n1mm_packets"):
                self.n1mm.radio_info["FunctionKeyCaption"] = self.F2.text()
            self.cw.sendcw(f"{self.process_macro(self.F2.toolTip())} ")

    def sendf3(self):
        """send f3"""
        if self.cw is not None:
            self.infoline.setText(f"Sending {self.process_macro(self.F3.toolTip())}")
            if self.preference.get("send_n1mm_packets"):
                self.n1mm.radio_info["FunctionKeyCaption"] = self.F3.text()
            self.cw.sendcw(f"{self.process_macro(self.F3.toolTip())} ")

    def sendf4(self):
        """send f4"""
        if self.cw is not None:
            self.infoline.setText(f"Sending {self.process_macro(self.F4.toolTip())}")
            if self.preference.get("send_n1mm_packets"):
                self.n1mm.radio_info["FunctionKeyCaption"] = self.F4.text()
            self.cw.sendcw(f"{self.process_macro(self.F4.toolTip())} ")

    def sendf5(self):
        """send f5"""
        if self.cw is not None:
            self.infoline.setText(f"Sending {self.process_macro(self.F5.toolTip())}")
            if self.preference.get("send_n1mm_packets"):
                self.n1mm.radio_info["FunctionKeyCaption"] = self.F5.text()
            self.cw.sendcw(f"{self.process_macro(self.F5.toolTip())} ")

    def sendf6(self):
        """send f6"""
        if self.cw is not None:
            self.infoline.setText(f"Sending {self.process_macro(self.F6.toolTip())}")
            if self.preference.get("send_n1mm_packets"):
                self.n1mm.radio_info["FunctionKeyCaption"] = self.F6.text()
            self.cw.sendcw(f"{self.process_macro(self.F6.toolTip())} ")

    def sendf7(self):
        """send f7"""
        if self.cw is not None:
            self.infoline.setText(f"Sending {self.process_macro(self.F7.toolTip())}")
            if self.preference.get("send_n1mm_packets"):
                self.n1mm.radio_info["FunctionKeyCaption"] = self.F7.text()
            self.cw.sendcw(f"{self.process_macro(self.F7.toolTip())} ")

    def sendf8(self):
        """send f8"""
        if self.cw is not None:
            self.infoline.setText(f"Sending {self.process_macro(self.F8.toolTip())}")
            if self.preference.get("send_n1mm_packets"):
                self.n1mm.radio_info["FunctionKeyCaption"] = self.F8.text()
            self.cw.sendcw(f"{self.process_macro(self.F8.toolTip())} ")

    def sendf9(self):
        """send f9"""
        if self.cw is not None:
            self.infoline.setText(f"Sending {self.process_macro(self.F9.toolTip())}")
            if self.preference.get("send_n1mm_packets"):
                self.n1mm.radio_info["FunctionKeyCaption"] = self.F9.text()
            self.cw.sendcw(f"{self.process_macro(self.F9.toolTip())} ")

    def sendf10(self):
        """send f10"""
        if self.cw is not None:
            self.infoline.setText(f"Sending {self.process_macro(self.F10.toolTip())}")
            if self.preference.get("send_n1mm_packets"):
                self.n1mm.radio_info["FunctionKeyCaption"] = self.F10.text()
            self.cw.sendcw(f"{self.process_macro(self.F10.toolTip())} ")

    def sendf11(self):
        """send f11"""
        if self.cw is not None:
            self.infoline.setText(f"Sending {self.process_macro(self.F11.toolTip())}")
            if self.preference.get("send_n1mm_packets"):
                self.n1mm.radio_info["FunctionKeyCaption"] = self.F11.text()
            self.cw.sendcw(f"{self.process_macro(self.F11.toolTip())} ")

    def sendf12(self):
        """send f12"""
        if self.cw is not None:
            self.infoline.setText(f"Sending {self.process_macro(self.F12.toolTip())}")
            if self.preference.get("send_n1mm_packets"):
                self.n1mm.radio_info["FunctionKeyCaption"] = self.F12.text()
            self.cw.sendcw(f"{self.process_macro(self.F12.toolTip())} ")

    def clearinputs(self):
        """clear text entry fields"""
        self.callsign_entry.clear()
        self.class_entry.clear()
        self.section_entry.clear()
        self.callsign_entry.setFocus()

    def changeband(self):
        """change band"""
        if self.band != self.band_selector.currentText():
            self.band = self.band_selector.currentText()
            if self.cat_control:
                self.cat_control.set_vfo(
                    int(float(self.fakefreq(self.band, self.mode)) * 1000)
                )
            self.send_status_udp()

    def changemode(self):
        """change mode"""
        if self.mode != self.mode_selector.currentText():
            self.mode = self.mode_selector.currentText()
            if self.mode == "PH":
                if int(self.oldfreq) < 10000000:
                    self.cat_control.set_mode("LSB")
                else:
                    self.cat_control.set_mode("USB")
            self.cat_control.set_mode(self.mode)
            self.send_status_udp()

    def changepower(self):
        """change power"""
        self.preference["power"] = str(self.power_selector.value())
        self.writepreferences()

    def lookupmygrid(self):
        """lookup my own gridsquare"""
        if self.look_up:
            self.mygrid, _, _, _ = self.look_up.lookup(self.mycallEntry.text())
            logger.info("my grid: %s", self.mygrid)

    def changemycall(self):
        """change my call"""
        text = self.mycallEntry.text()
        if len(text):
            if text[-1] == " ":  # allow only alphanumerics or slashes
                self.mycallEntry.setText(text.strip())
            else:
                cleaned = "".join(
                    ch for ch in text if ch.isalnum() or ch == "/"
                ).upper()
                self.mycallEntry.setText(cleaned)
        self.preference["mycall"] = self.mycallEntry.text()
        if self.preference["mycall"] != "":
            self.mycallEntry.setStyleSheet("border: 1px solid green;")
            _thethread = threading.Thread(
                target=self.lookupmygrid,
                daemon=True,
            )
            _thethread.start()
        else:
            self.mycallEntry.setStyleSheet("border: 1px solid red;")
        self.writepreferences()

    def changemyclass(self):
        """change class"""
        text = self.myclassEntry.text()
        if len(text):
            if text[-1] == " ":  # allow only alphanumerics
                self.myclassEntry.setText(text.strip())
            else:
                cleaned = "".join(ch for ch in text if ch.isalnum()).upper()
                self.myclassEntry.setText(cleaned)
        self.preference["myclass"] = self.myclassEntry.text()
        if self.preference["myclass"] != "":
            self.myclassEntry.setStyleSheet("border: 1px solid green;")
        else:
            self.myclassEntry.setStyleSheet("border: 1px solid red;")
        self.writepreferences()

    def changemysection(self):
        """change section"""
        text = self.mysectionEntry.text()
        if len(text):
            if text[-1] == " ":  # allow only alphanumerics
                self.mysectionEntry.setText(text.strip())
            else:
                cleaned = "".join(ch for ch in text if ch.isalpha()).upper()
                self.mysectionEntry.setText(cleaned)
        self.preference["mysection"] = self.mysectionEntry.text()
        if self.preference["mysection"] != "":
            self.mysectionEntry.setStyleSheet("border: 1px solid green;")
        else:
            self.mysectionEntry.setStyleSheet("border: 1px solid red;")
        self.writepreferences()

    def is_floatable(self, item: str) -> bool:
        """check to see if string can be a float"""
        if item.isnumeric():
            return True
        try:
            _test = float(item)
        except ValueError:
            return False
        return True

    def calltest(self):
        """
        Test and strip callsign of bad characters, advance to next input field if space pressed.
        """
        text = self.callsign_entry.text()
        if len(text):
            if text[-1] == " ":
                self.callsign_entry.setText(text.strip())
                if self.is_floatable(self.callsign_entry.text()):
                    vfo = float(text.strip())
                    vfo = int(vfo * 1000)
                    self.set_fakefreq(vfo)
                    if self.cat_control:
                        self.cat_control.set_vfo(str(vfo))
                    self.clearinputs()
                    return
                _thethread = threading.Thread(
                    target=self.lazy_lookup,
                    args=(self.callsign_entry.text(),),
                    daemon=True,
                )
                _thethread.start()
                self.class_entry.setFocus()
                self.class_entry.deselect()
            else:
                washere = self.callsign_entry.cursorPosition()
                cleaned = "".join(
                    ch for ch in text if ch.isalnum() or ch == "/" or ch == "."
                ).upper()
                self.callsign_entry.setText(cleaned)
                self.callsign_entry.setCursorPosition(washere)
                if cleaned == "OPON":
                    self.get_opon()
                    self.clearinputs()
                    return
                self.super_check()

    def classtest(self):
        """
        Test and strip class of bad characters, advance to next input field if space pressed.
        """
        text = self.class_entry.text()
        if len(text):
            if text[-1] == " ":
                self.class_entry.setText(text.strip())
                self.section_entry.setFocus()
                self.section_entry.deselect()
            else:
                washere = self.class_entry.cursorPosition()
                cleaned = "".join(ch for ch in text if ch.isalnum()).upper()
                self.class_entry.setText(cleaned)
                self.class_entry.setCursorPosition(washere)

    def sectiontest(self):
        """
        Test and strip section of bad characters, advance to next input field if space pressed.
        """
        text = self.section_entry.text()
        if len(text):
            if text[-1] == " ":
                self.section_entry.setText(text.strip())
                self.callsign_entry.setFocus()
                self.callsign_entry.deselect()
            else:
                washere = self.section_entry.cursorPosition()
                cleaned = "".join(ch for ch in text if ch.isalpha()).upper()
                self.section_entry.setText(cleaned)
                self.section_entry.setCursorPosition(washere)

    @staticmethod
    def highlighted(state):
        """
        Return CSS foreground highlight color if state is true,
        otherwise return an empty string.
        """
        if state:
            return "color: rgb(245, 121, 0);"
        return ""

    def readpreferences(self):
        """
        Restore preferences if they exist, otherwise create some sane defaults.
        """
        try:
            if os.path.exists("./fd_preferences.json"):
                with open(
                    "./fd_preferences.json", "rt", encoding="utf-8"
                ) as file_descriptor:
                    self.preference = loads(file_descriptor.read())
            else:
                with open(
                    "./fd_preferences.json", "wt", encoding="utf-8"
                ) as file_descriptor:
                    file_descriptor.write(dumps(self.preference, indent=4))
                    logger.info("No preference, writing dafult.")
        except IOError as exception:
            logger.critical("readpreferences: %s", exception)
        logger.info(self.preference)
        try:
            self.mycallEntry.setText(self.preference["mycall"])
            if self.preference["mycall"] != "":
                self.mycallEntry.setStyleSheet("border: 1px solid green;")
            self.myclassEntry.setText(self.preference["myclass"])
            if self.preference["myclass"] != "":
                self.myclassEntry.setStyleSheet("border: 1px solid green;")
            self.mysectionEntry.setText(self.preference["mysection"])
            if self.preference["mysection"] != "":
                self.mysectionEntry.setStyleSheet("border: 1px solid green;")

            self.power_selector.setValue(int(self.preference["power"]))

            self.cat_control = None
            if self.preference["useflrig"]:
                self.cat_control = CAT(
                    "flrig", self.preference["CAT_ip"], self.preference["CAT_port"]
                )
            if self.preference["userigctld"]:
                self.cat_control = CAT(
                    "rigctld", self.preference["CAT_ip"], self.preference["CAT_port"]
                )

            if self.preference["useqrz"]:
                self.look_up = QRZlookup(
                    self.preference["lookupusername"], self.preference["lookuppassword"]
                )
                self.callbook_icon.setText("QRZ")
                if self.look_up.session:
                    self.callbook_icon.setStyleSheet("color: rgb(128, 128, 0);")
                else:
                    self.callbook_icon.setStyleSheet("color: rgb(136, 138, 133);")

            if self.preference["usehamdb"]:
                self.look_up = HamDBlookup()
                self.callbook_icon.setText("HamDB")
                self.callbook_icon.setStyleSheet("color: rgb(128, 128, 0);")

            if self.preference["usehamqth"]:
                self.look_up = HamQTH(
                    self.preference["lookupusername"],
                    self.preference["lookuppassword"],
                )
                self.callbook_icon.setText("HamQTH")
                if self.look_up.session:
                    self.callbook_icon.setStyleSheet("color: rgb(128, 128, 0);")
                else:
                    self.callbook_icon.setStyleSheet("color: rgb(136, 138, 133);")

            self.cloudlogauth()

            if self.preference["cwtype"] == 0:
                self.cw = None
            else:
                self.cw = CW(
                    self.preference["cwtype"],
                    self.preference["cwip"],
                    self.preference["cwport"],
                )
                self.cw.speed = 20

            self.connect_to_server = self.preference.get("useserver")
            self.multicast_group = self.preference.get("multicast_group")
            self.multicast_port = self.preference.get("multicast_port")
            self.interface_ip = self.preference.get("interface_ip")
            # group upd server
            logger.info("Use group server: %s", self.connect_to_server)
            if self.connect_to_server:
                logger.info(
                    "Connecting: %s:%s %s",
                    self.multicast_group,
                    self.multicast_port,
                    self.interface_ip,
                )
                self.chat_window.show()
                self.frame_5.hide()
                self.frame_6.hide()
                self.frame_7.hide()
                self.frame_8.hide()
                self.frame_9.hide()
                self.group_call_indicator.show()
                self.mycallEntry.hide()
                self.server_udp = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                if sys.platform.startswith("darwin"):
                    self.server_udp.setsockopt(
                        socket.SOL_SOCKET, socket.SO_REUSEPORT, 1
                    )
                else:
                    self.server_udp.setsockopt(
                        socket.SOL_SOCKET, socket.SO_REUSEADDR, 1
                    )
                self.server_udp.bind(("", int(self.multicast_port)))
                mreq = socket.inet_aton(self.multicast_group) + socket.inet_aton(
                    self.interface_ip
                )
                self.server_udp.setsockopt(
                    socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, bytes(mreq)
                )
                self.server_udp.settimeout(0.01)

                if self._udpwatch is None:
                    self._udpwatch = threading.Thread(
                        target=self.watch_udp,
                        daemon=True,
                    )
                    self._udpwatch.start()
            else:
                self.groupcall = None
                self.chat_window.hide()
                self.frame_5.show()
                self.frame_6.show()
                self.frame_7.show()
                self.frame_8.show()
                self.frame_9.show()
                self.group_call_indicator.hide()
                self.mycallEntry.show()

            self.n1mm = N1MM(
                ip_address=self.preference.get("n1mm_ip"),
                radioport=self.preference.get("n1mm_radioport"),
                contactport=self.preference.get("n1mm_contactport"),
            )
            self.n1mm.set_station_name(self.preference.get("n1mm_station_name"))
            self.n1mm.set_operator(self.preference.get("n1mm_operator"))

        except KeyError as err:
            logger.warning("Corrupt preference, %s, loading clean version.", err)
            self.preference = self.reference_preference.copy()
            with open(
                "./fd_preferences.json", "wt", encoding="utf-8"
            ) as file_descriptor:
                file_descriptor.write(dumps(self.preference, indent=4))
                logger.info("writing: %s", self.preference)

    def writepreferences(self):
        """
        Write preferences to json file.
        """
        try:
            with open(
                "./fd_preferences.json", "wt", encoding="utf-8"
            ) as file_descriptor:
                file_descriptor.write(dumps(self.preference, indent=4))
                logger.info("writing: %s", self.preference)
        except IOError as exception:
            logger.critical("writepreferences: %s", exception)

    def log_contact(self):
        """Log the current contact"""
        self.show_dirty_records()
        if (
            len(self.callsign_entry.text()) == 0
            or len(self.class_entry.text()) == 0
            or len(self.section_entry.text()) == 0
        ):
            return
        if not self.cat_control:
            self.oldfreq = int(float(self.fakefreq(self.band, self.mode)) * 1000)
        unique_id = uuid.uuid4().hex
        contact = (
            self.callsign_entry.text(),
            self.class_entry.text(),
            self.section_entry.text(),
            self.oldfreq,
            self.band,
            self.mode,
            int(self.power_selector.value()),
            self.contactlookup["grid"],
            self.contactlookup["name"],
            unique_id,
        )
        self.db.log_contact(contact)

        stale = datetime.now() + timedelta(seconds=30)
        if self.connect_to_server:
            contact = {
                "cmd": "POST",
                "hiscall": self.callsign_entry.text(),
                "class": self.class_entry.text(),
                "section": self.section_entry.text(),
                "mode": self.mode,
                "band": self.band,
                "frequency": self.oldfreq,
                "date_and_time": datetime.now(dt.timezone.utc).strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
                "power": int(self.power_selector.value()),
                "grid": self.contactlookup["grid"],
                "opname": self.contactlookup["name"],
                "station": self.preference["mycall"],
                "unique_id": unique_id,
                "expire": stale.isoformat(),
            }
            self.server_commands.append(contact)
            bytesToSend = bytes(dumps(contact), encoding="ascii")
            try:
                self.server_udp.sendto(
                    bytesToSend, (self.multicast_group, int(self.multicast_port))
                )
            except OSError as err:
                logger.warning("%s", err)

        if self.preference.get("send_n1mm_packets"):
            if self.oldfreq == 0:
                self.n1mm.contact_info["rxfreq"] = str(
                    self.fakefreq(self.band, self.mode)
                )
                self.n1mm.contact_info["txfreq"] = str(
                    self.fakefreq(self.band, self.mode)
                )
            else:
                self.n1mm.contact_info["rxfreq"] = str(self.oldfreq)[:-1]
                self.n1mm.contact_info["txfreq"] = str(self.oldfreq)[:-1]

            self.n1mm.contact_info["mode"] = self.oldmode
            if self.oldmode in ("CW", "DG"):
                self.n1mm.contact_info["points"] = "2"
            else:
                self.n1mm.contact_info["points"] = "1"
            self.n1mm.contact_info["band"] = self.n1mm.bandToUDPBand[self.band]
            self.n1mm.contact_info["mycall"] = self.preference.get("mycall")
            self.n1mm.contact_info["IsRunQSO"] = str(self.run_state)
            self.n1mm.contact_info["timestamp"] = datetime.now(
                dt.timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S")
            self.n1mm.contact_info["call"] = self.callsign_entry.text()
            self.n1mm.contact_info["gridsquare"] = self.contactlookup.get("grid")
            self.n1mm.contact_info["exchange1"] = self.class_entry.text()
            self.n1mm.contact_info["section"] = self.section_entry.text()
            self.n1mm.contact_info["name"] = self.contactlookup.get("name")
            self.n1mm.contact_info["power"] = self.power_selector.value()
            self.n1mm.contact_info["ID"] = unique_id
            self.n1mm.send_contact_info()

        self.sections()
        self.stats()
        self.updatemarker()
        self.logwindow()
        self.clearinputs()
        self.postcloudlog()
        self.clearcontactlookup()

    def stats(self):
        """
        Get an idea of how you're doing points wise.
        """
        (
            cwcontacts,
            phonecontacts,
            digitalcontacts,
            bandmodemult,
            last15,
            lasthour,
            _,
            _,
        ) = self.db.stats()

        self.Total_CW.setText(str(cwcontacts))
        self.Total_Phone.setText(str(phonecontacts))
        self.Total_Digital.setText(str(digitalcontacts))
        self.bandmodemult = bandmodemult
        self.QSO_Last15.setText(str(last15))
        self.QSO_PerHour.setText(str(lasthour))
        self.QSO_Points.setText(str(self.calcscore()))

    def calcscore(self):
        """
        Return our current score based on operating power,
        altpower and types of contacts.

        2022 scoring: contacts over 100w are disallowed.
        QRP and Low Power (<100W) have base multiplier of 2.
        QRP with Alt Power has base multiplier of 5
        """
        self.qrpcheck()
        c_dubs, phone, digital = self.db.contacts_under_101watts()
        self.score = (int(c_dubs) * 2) + int(phone) + (int(digital) * 2)
        self.basescore = self.score
        multiplier = 2
        if self.qrp and self.preference["altpower"]:
            multiplier = 5
        self.score = self.score * multiplier
        return self.score

    def qrpcheck(self):
        """qrp = 5W cw, 10W ph and di, highpower not allowed in 2022"""
        self.qrp, self.highpower = self.db.qrp_check()

    def logwindow(self):
        """Populate log window with contacts"""
        self.dupdict = {}
        self.listWidget.clear()
        log = self.db.fetch_all_contacts_desc()
        for contact in log:
            (
                logid,
                hiscall,
                hisclass,
                hissection,
                the_datetime,
                frequency,
                band,
                mode,
                power,
                _,
                _,
                _,
                _,
            ) = contact
            logline = (
                f"{str(logid).rjust(3,'0')} {hiscall.ljust(15)} {hisclass.rjust(3)} "
                f"{hissection.rjust(3)} {the_datetime} {str(frequency).rjust(9)} "
                f"{str(band).rjust(3)}M {mode} {str(power).rjust(3)}W"
            )
            self.listWidget.addItem(logline)
            self.dupdict[f"{hiscall}{band}{mode}"] = True

    def qsoedited(self):
        """
        Perform functions after QSO edited or deleted.
        """
        self.sections()
        self.stats()
        self.logwindow()

    def qsoclicked(self):
        """
        Gets the line of the log clicked on, and passes that line to the edit dialog.
        """
        item = self.listWidget.currentItem()
        self.linetopass = item.text()
        dialog = EditQSODialog(self)
        dialog.set_up(self.linetopass, self.db)
        dialog.change.lineChanged.connect(self.qsoedited)
        dialog.open()

    def read_sections(self):
        """
        Reads in the ARRL sections into some internal dictionaries.
        """
        try:
            data_path = self.working_path + "/data/arrl_sect.dat"
            with open(data_path, "r", encoding="utf-8") as file_descriptor:
                while 1:
                    line = (
                        file_descriptor.readline().strip()
                    )  # read a line and put in db
                    if not line:
                        break
                    if line[0] == "#":
                        continue
                    try:
                        _, state, canum, abbrev, name = str.split(line, None, 4)
                        self.secName[abbrev] = abbrev + " " + name + " " + canum
                        self.secState[abbrev] = state
                        for i in range(len(abbrev) - 1):
                            partial = abbrev[: -i - 1]
                            self.secPartial[partial] = 1
                    except ValueError as exception:
                        logger.warning("read_sections: %s", exception)
        except IOError as exception:
            logger.critical("read_sections: read error: %s", exception)

    def section_check(self):
        """
        Shows you the possible section matches
        based on what you have typed in the section input filed.
        """
        self.infobox.clear()
        self.infobox.setTextColor(QtGui.QColor(211, 215, 207))
        sec = self.section_entry.text()
        if sec == "":
            sec = "^"
        listofkeys = list(self.secName.keys())
        newlist = list(filter(lambda y: y.startswith(sec), listofkeys))
        for listitem in newlist:
            self.infobox.insertPlainText(self.secName[listitem] + "\n")

    def read_scp(self):
        """
        Reads in a list of known contesters into an internal dictionary
        """
        try:
            data_path = self.working_path + "/data/MASTER.SCP"
            with open(data_path, "r", encoding="utf-8") as file_descriptor:
                self.scp = file_descriptor.readlines()
                self.scp = list(map(lambda x: x.strip(), self.scp))
        except IOError as exception:
            logger.critical("read_scp: read error: %s", exception)

    def super_check(self):
        """
        Performs a supercheck partial on the callsign entered in the field.
        """
        self.infobox.clear()
        self.infobox.setTextColor(QtGui.QColor(211, 215, 207))
        acall = self.callsign_entry.text()
        if len(acall) > 2:
            matches = list(filter(lambda x: x.startswith(acall), self.scp))
            for match in matches:
                self.infobox.insertPlainText(match + " ")

    def dup_check(self):
        """check for duplicates"""
        self.check_dupe_status_udp()
        acall = self.callsign_entry.text()
        self.infobox.clear()
        log = self.db.dup_check(acall)
        for contact in log:
            hiscall, hisclass, hissection, hisband, hismode = contact
            if len(self.class_entry.text()) == 0:
                self.class_entry.setText(hisclass)
            if len(self.section_entry.text()) == 0:
                self.section_entry.setText(hissection)
            dupetext = ""
            if hisband == self.band and hismode == self.mode:
                self.flash()
                self.infobox.setTextColor(QtGui.QColor(245, 121, 0))
                dupetext = " DUPE"
            else:
                self.infobox.setTextColor(QtGui.QColor(211, 215, 207))
            self.infobox.insertPlainText(f"{hiscall}: {hisband} {hismode}{dupetext}\n")

    def worked_sections(self):
        """get sections worked"""
        all_rows = self.db.sections()
        self.wrkdsections = str(all_rows)
        self.wrkdsections = (
            self.wrkdsections.replace("('", "")
            .replace("',), ", ",")
            .replace("',)]", "")
            .replace("[", "")
            .split(",")
        )

    def worked_section(self, section):
        """
        Return CSS foreground value for section based on if it has been worked.
        """
        if section in self.wrkdsections:
            return "color: rgb(245, 121, 0);"
        return "color: rgb(136, 138, 133);"

    def sections_col1(self):
        """display sections worked"""
        self.Section_DX.setStyleSheet(self.worked_section("DX"))
        self.Section_CT.setStyleSheet(self.worked_section("CT"))
        self.Section_RI.setStyleSheet(self.worked_section("RI"))
        self.Section_EMA.setStyleSheet(self.worked_section("EMA"))
        self.Section_VT.setStyleSheet(self.worked_section("VT"))
        self.Section_ME.setStyleSheet(self.worked_section("ME"))
        self.Section_WMA.setStyleSheet(self.worked_section("WMA"))
        self.Section_NH.setStyleSheet(self.worked_section("NH"))
        self.Section_ENY.setStyleSheet(self.worked_section("ENY"))
        self.Section_NNY.setStyleSheet(self.worked_section("NNY"))
        self.Section_NLI.setStyleSheet(self.worked_section("NLI"))
        self.Section_SNJ.setStyleSheet(self.worked_section("SNJ"))
        self.Section_NNJ.setStyleSheet(self.worked_section("NNJ"))
        self.Section_WNY.setStyleSheet(self.worked_section("WNY"))

    def sections_col2(self):
        """display sections worked"""
        self.Section_DE.setStyleSheet(self.worked_section("DE"))
        self.Section_MDC.setStyleSheet(self.worked_section("MDC"))
        self.Section_EPA.setStyleSheet(self.worked_section("EPA"))
        self.Section_WPA.setStyleSheet(self.worked_section("WPA"))
        self.Section_AL.setStyleSheet(self.worked_section("AL"))
        self.Section_SC.setStyleSheet(self.worked_section("SC"))
        self.Section_GA.setStyleSheet(self.worked_section("GA"))
        self.Section_SFL.setStyleSheet(self.worked_section("SFL"))
        self.Section_KY.setStyleSheet(self.worked_section("KY"))
        self.Section_TN.setStyleSheet(self.worked_section("TN"))
        self.Section_NC.setStyleSheet(self.worked_section("NC"))
        self.Section_VA.setStyleSheet(self.worked_section("VA"))
        self.Section_NFL.setStyleSheet(self.worked_section("NFL"))
        self.Section_VI.setStyleSheet(self.worked_section("VI"))
        self.Section_PR.setStyleSheet(self.worked_section("PR"))
        self.Section_WCF.setStyleSheet(self.worked_section("WCF"))

    def sections_col3(self):
        """display sections worked"""
        self.Section_AR.setStyleSheet(self.worked_section("AR"))
        self.Section_NTX.setStyleSheet(self.worked_section("NTX"))
        self.Section_LA.setStyleSheet(self.worked_section("LA"))
        self.Section_OK.setStyleSheet(self.worked_section("OK"))
        self.Section_MS.setStyleSheet(self.worked_section("MS"))
        self.Section_STX.setStyleSheet(self.worked_section("STX"))
        self.Section_NM.setStyleSheet(self.worked_section("NM"))
        self.Section_WTX.setStyleSheet(self.worked_section("WTX"))
        self.Section_EB.setStyleSheet(self.worked_section("EB"))
        self.Section_SCV.setStyleSheet(self.worked_section("SCV"))
        self.Section_LAX.setStyleSheet(self.worked_section("LAX"))
        self.Section_SDG.setStyleSheet(self.worked_section("SDG"))
        self.Section_ORG.setStyleSheet(self.worked_section("ORG"))
        self.Section_SF.setStyleSheet(self.worked_section("SF"))
        self.Section_PAC.setStyleSheet(self.worked_section("PAC"))
        self.Section_SJV.setStyleSheet(self.worked_section("SJV"))
        self.Section_SB.setStyleSheet(self.worked_section("SB"))
        self.Section_SV.setStyleSheet(self.worked_section("SV"))

    def sections_col4(self):
        """display sections worked"""
        self.Section_AK.setStyleSheet(self.worked_section("AK"))
        self.Section_NV.setStyleSheet(self.worked_section("NV"))
        self.Section_AZ.setStyleSheet(self.worked_section("AZ"))
        self.Section_OR.setStyleSheet(self.worked_section("OR"))
        self.Section_EWA.setStyleSheet(self.worked_section("EWA"))
        self.Section_UT.setStyleSheet(self.worked_section("UT"))
        self.Section_ID.setStyleSheet(self.worked_section("ID"))
        self.Section_WWA.setStyleSheet(self.worked_section("WWA"))
        self.Section_MT.setStyleSheet(self.worked_section("MT"))
        self.Section_WY.setStyleSheet(self.worked_section("WY"))
        self.Section_MI.setStyleSheet(self.worked_section("MI"))
        self.Section_WV.setStyleSheet(self.worked_section("WV"))
        self.Section_OH.setStyleSheet(self.worked_section("OH"))
        self.Section_IL.setStyleSheet(self.worked_section("IL"))
        self.Section_WI.setStyleSheet(self.worked_section("WI"))
        self.Section_IN.setStyleSheet(self.worked_section("IN"))

    def sections_col5(self):
        """display sections worked"""
        self.Section_CO.setStyleSheet(self.worked_section("CO"))
        self.Section_MO.setStyleSheet(self.worked_section("MO"))
        self.Section_IA.setStyleSheet(self.worked_section("IA"))
        self.Section_ND.setStyleSheet(self.worked_section("ND"))
        self.Section_KS.setStyleSheet(self.worked_section("KS"))
        self.Section_NE.setStyleSheet(self.worked_section("NE"))
        self.Section_MN.setStyleSheet(self.worked_section("MN"))
        self.Section_SD.setStyleSheet(self.worked_section("SD"))

        self.Section_AB.setStyleSheet(self.worked_section("AB"))
        self.Section_BC.setStyleSheet(self.worked_section("BC"))
        self.Section_GH.setStyleSheet(self.worked_section("GH"))
        self.Section_MB.setStyleSheet(self.worked_section("MB"))
        self.Section_NB.setStyleSheet(self.worked_section("NB"))
        self.Section_NL.setStyleSheet(self.worked_section("NL"))
        self.Section_NS.setStyleSheet(self.worked_section("NS"))

        self.Section_PE.setStyleSheet(self.worked_section("PE"))
        self.Section_ONE.setStyleSheet(self.worked_section("ONE"))
        self.Section_ONN.setStyleSheet(self.worked_section("ONN"))
        self.Section_ONS.setStyleSheet(self.worked_section("ONS"))
        self.Section_QC.setStyleSheet(self.worked_section("QC"))
        self.Section_SK.setStyleSheet(self.worked_section("SK"))
        self.Section_TER.setStyleSheet(self.worked_section("TER"))

    def sections(self):
        """
        Updates onscreen sections highlighting the ones worked.
        """
        self.worked_sections()
        self.sections_col1()
        self.sections_col2()
        self.sections_col3()
        self.sections_col4()
        self.sections_col5()

    def get_band_mode_tally(self, band, mode):
        """
        Returns the amount of contacts and the maximum power
        used for a particular band/mode combination.
        """
        return self.db.get_band_mode_tally(band, mode)

    def getbands(self):
        """
        Returns a list of bands worked, and an empty list if none worked.
        """
        bandlist = []
        list_o_bands = self.db.get_bands()
        if list_o_bands:
            for count in list_o_bands:
                bandlist.append(count[0])
            return bandlist
        return []

    def generate_band_mode_tally(self):
        """generates band mode tally"""
        blist = self.getbands()
        bmtfn = "Statistics.txt"
        try:
            with open(bmtfn, "w", encoding="utf-8") as file_descriptor:
                print("\t\tCW\tPWR\tDI\tPWR\tPH\tPWR", end="\r\n", file=file_descriptor)
                print("-" * 60, end="\r\n", file=file_descriptor)
                for band in self.bands:
                    if band in blist:
                        cwt = self.get_band_mode_tally(band, "CW")
                        dit = self.get_band_mode_tally(band, "DI")
                        pht = self.get_band_mode_tally(band, "PH")
                        print(
                            f"Band:\t{band}\t{cwt[0]}\t{cwt[1]}\t{dit[0]}"
                            f"\t{dit[1]}\t{pht[0]}\t{pht[1]}",
                            end="\r\n",
                            file=file_descriptor,
                        )
                        print("-" * 60, end="\r\n", file=file_descriptor)
        except IOError as exception:
            logger.critical("generate_band_mode_tally: write error: %s", exception)

    def get_state(self, section):
        """
        Returns the US state a section is in, or Bool False if none was found.
        """
        try:
            state = self.secState[section]
            if state != "--":
                return state
        except IndexError:
            return False
        except KeyError:
            return False
        return False

    @staticmethod
    def gridtolatlon(maiden):
        """
        Converts a maidenhead gridsquare to a latitude longitude pair.
        """
        maiden = str(maiden).strip().upper()

        length = len(maiden)
        if not 8 >= length >= 2 and length % 2 == 0:
            return 0, 0

        lon = (ord(maiden[0]) - 65) * 20 - 180
        lat = (ord(maiden[1]) - 65) * 10 - 90

        if length >= 4:
            lon += (ord(maiden[2]) - 48) * 2
            lat += ord(maiden[3]) - 48

        if length >= 6:
            lon += (ord(maiden[4]) - 65) / 12 + 1 / 24
            lat += (ord(maiden[5]) - 65) / 24 + 1 / 48

        if length >= 8:
            lon += (ord(maiden[6])) * 5.0 / 600
            lat += (ord(maiden[7])) * 2.5 / 600

        return lat, lon

    def updatemarker(self):
        """
        Updates the xplanet marker file with a list of logged contact lat & lon
        """
        if self.preference["usemarker"]:
            filename = str(Path.home()) + "/" + self.preference.get("markerfile", "")
            try:
                list_of_grids = self.db.get_grids()
                if list_of_grids:
                    lastcolor = ""
                    with open(filename, "w", encoding="ascii") as file_descriptor:
                        islast = len(list_of_grids) - 1
                        for count, grid in enumerate(list_of_grids):
                            if count == islast:
                                lastcolor = "color=Orange"
                            if len(grid[0]) > 1:
                                lat, lon = self.gridtolatlon(grid[0])
                                print(
                                    f'{lat} {lon} "" {lastcolor}',
                                    end="\r\n",
                                    file=file_descriptor,
                                )
            except IOError as exception:
                logger.warning(
                    "updatemarker: error %s writing to %s", exception, filename
                )
                self.infobox.setTextColor(QtGui.QColor(245, 121, 0))
                self.infobox.insertPlainText(f"Unable to write to {filename}\n")

    def adif(self):
        """
        Creates an ADIF file of the contacts made.
        """
        logname = "FieldDay.adi"
        self.infobox.setTextColor(QtGui.QColor(211, 215, 207))
        self.infobox.insertPlainText(f"Saving ADIF to: {logname}\n")
        app.processEvents()
        log = self.db.fetch_all_contacts_asc()
        if not log:
            return
        grid = False
        opname = False
        try:
            with open(logname, "w", encoding="ascii") as file_descriptor:
                print("<ADIF_VER:5>2.2.0", end="\r\n", file=file_descriptor)
                print("<EOH>", end="\r\n", file=file_descriptor)
                for contact in log:
                    (
                        _,
                        hiscall,
                        hisclass,
                        hissection,
                        the_datetime,
                        freq,
                        band,
                        mode,
                        _,
                        grid,
                        opname,
                        _,
                        _,
                    ) = contact
                    if mode == "DI":
                        mode = "FT8"
                    if mode == "PH":
                        mode = "SSB"
                    if mode == "CW":
                        rst = "599"
                    else:
                        rst = "59"
                    loggeddate = the_datetime[:10]
                    loggedtime = the_datetime[11:13] + the_datetime[14:16]
                    try:
                        temp = str(freq / 1000000).split(".")
                        freq = temp[0] + "." + temp[1].ljust(3, "0")
                    except TypeError:
                        freq = "UNKNOWN"

                    if freq == "0.000":  # incase no freq was logged
                        freq = int(self.fakefreq(band, mode))
                        temp = str(freq / 1000).split(".")
                        freq = temp[0] + "." + temp[1].ljust(3, "0")

                    print(
                        f"<QSO_DATE:{len(''.join(loggeddate.split('-')))}:d>"
                        f"{''.join(loggeddate.split('-'))}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                    print(
                        f"<TIME_ON:{len(loggedtime)}>{loggedtime}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                    print(
                        f"<CALL:{len(hiscall)}>{hiscall}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                    print(f"<MODE:{len(mode)}>{mode}", end="\r\n", file=file_descriptor)
                    print(
                        f"<BAND:{len(band + 'M')}>{band + 'M'}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                    print(f"<FREQ:{len(freq)}>{freq}", end="\r\n", file=file_descriptor)
                    print(
                        f"<RST_SENT:{len(rst)}>{rst}", end="\r\n", file=file_descriptor
                    )
                    print(
                        f"<RST_RCVD:{len(rst)}>{rst}", end="\r\n", file=file_descriptor
                    )
                    print(
                        "<STX_STRING:"
                        f"{len(self.preference['myclass'] + ' ' + self.preference['mysection'])}>"
                        f"{self.preference['myclass'] + ' ' + self.preference['mysection']}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                    print(
                        f"<SRX_STRING:{len(hisclass + ' ' + hissection)}>"
                        f"{hisclass + ' ' + hissection}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                    print(
                        f"<ARRL_SECT:{len(hissection)}>{hissection}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                    print(
                        f"<CLASS:{len(hisclass)}>{hisclass}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                    state = self.get_state(hissection)
                    if state:
                        print(
                            f"<STATE:{len(state)}>{state}",
                            end="\r\n",
                            file=file_descriptor,
                        )
                    if len(grid) > 1:
                        print(
                            f"<GRIDSQUARE:{len(grid)}>{grid}",
                            end="\r\n",
                            file=file_descriptor,
                        )
                    if len(opname) > 1:
                        print(
                            f"<NAME:{len(opname)}>{opname}",
                            end="\r\n",
                            file=file_descriptor,
                        )
                    comment = "ARRL-FD"
                    print(
                        f"<COMMENT:{len(comment)}>{comment}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                    print("<EOR>", end="\r\n", file=file_descriptor)
                    print("", end="\r\n", file=file_descriptor)
        except IOError as exception:
            logger.critical("adif: IO error: %s", exception)
        self.infobox.insertPlainText("Done\n\n")
        app.processEvents()

    def postcloudlog(self):
        """
        Log contact to Cloudlog: https://github.com/magicbug/Cloudlog
        """
        if (not self.preference["cloudlog"]) or (not self.cloudlogauthenticated):
            return
        contact = self.db.fetch_last_contact()
        if not contact:
            return
        (
            _,
            hiscall,
            hisclass,
            hissection,
            the_datetime,
            freq,
            band,
            mode,
            _,
            grid,
            opname,
            _,
            _,
        ) = contact
        if mode == "DI":
            mode = "FT8"
        if mode == "PH":
            mode = "SSB"
        if mode == "CW":
            rst = "599"
        else:
            rst = "59"
        loggeddate = the_datetime[:10]
        loggedtime = the_datetime[11:13] + the_datetime[14:16]
        adifq = (
            f"<QSO_DATE:{len(''.join(loggeddate.split('-')))}:d>"
            f"{''.join(loggeddate.split('-'))}"
        )
        adifq += f"<TIME_ON:{len(loggedtime)}>{loggedtime}"
        adifq += f"<CALL:{len(hiscall)}>{hiscall}"
        adifq += f"<MODE:{len(mode)}>{mode}"
        adifq += f"<BAND:{len(band + 'M')}>{band + 'M'}"
        freq = int(self.fakefreq(band, mode))
        temp = str(freq / 1000).split(".")
        freq = temp[0] + "." + temp[1].ljust(3, "0")
        adifq += f"<FREQ:{len(freq)}>{freq}"
        adifq += f"<RST_SENT:{len(rst)}>{rst}"
        adifq += f"<RST_RCVD:{len(rst)}>{rst}"
        adifq += (
            f"<STX_STRING:{len(self.preference['myclass'] + ' ' + self.preference['mysection'])}>"
            f"{self.preference['myclass'] + ' ' + self.preference['mysection']}"
        )
        adifq += (
            f"<SRX_STRING:{len(hisclass + ' ' + hissection)}>"
            f"{hisclass + ' ' + hissection}"
        )
        adifq += f"<ARRL_SECT:{len(hissection)}>{hissection}"
        adifq += f"<CLASS:{len(hisclass)}>{hisclass}"
        state = self.get_state(hissection)
        if state:
            adifq += f"<STATE:{len(state)}>{state}"
        if len(grid) > 1:
            adifq += f"<GRIDSQUARE:{len(grid)}>{grid}"
        if len(opname) > 1:
            adifq += f"<NAME:{len(opname)}>{opname}"
        adifq += "<CONTEST_ID:14>ARRL-FIELD-DAY"
        comment = "ARRL-FD"
        adifq += f"<COMMENT:{len(comment)}>{comment}"
        adifq += "<EOR>"

        payload_dict = {
            "key": self.preference["cloudlogapi"],
            "station_profile_id": self.preference["cloudlogstationid"],
            "type": "adif",
            "string": adifq,
        }
        json_data = dumps(payload_dict)
        _ = requests.post(self.preference["cloudlogurl"] + "qso/", json_data, timeout=5)

    def cabrillo(self):
        """
        Generates a cabrillo log file.
        """
        filename = self.preference["mycall"].upper() + ".log"
        self.infobox.setTextColor(QtGui.QColor(211, 215, 207))
        self.infobox.insertPlainText(f"Saving cabrillo to: {filename}\n")
        app.processEvents()
        log = self.db.fetch_all_contacts_asc()
        if not log:
            return
        catpower = ""
        if self.qrp:
            catpower = "QRP"
        elif self.highpower:
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
                    f"CALLSIGN: {self.preference['mycall']}",
                    end="\r\n",
                    file=file_descriptor,
                )
                print("LOCATION:", end="\r\n", file=file_descriptor)
                print(
                    f"ARRL-SECTION: {self.preference['mysection']}",
                    end="\r\n",
                    file=file_descriptor,
                )
                print(
                    f"CATEGORY: {self.preference['myclass']}",
                    end="\r\n",
                    file=file_descriptor,
                )
                print(f"CATEGORY-POWER: {catpower}", end="\r\n", file=file_descriptor)
                print(
                    f"CLAIMED-SCORE: {self.calcscore()}",
                    end="\r\n",
                    file=file_descriptor,
                )
                print(
                    f"OPERATORS: {self.preference['mycall']}",
                    end="\r\n",
                    file=file_descriptor,
                )
                print("NAME: ", end="\r\n", file=file_descriptor)
                print("ADDRESS: ", end="\r\n", file=file_descriptor)
                print("ADDRESS-CITY: ", end="\r\n", file=file_descriptor)
                print("ADDRESS-STATE: ", end="\r\n", file=file_descriptor)
                print("ADDRESS-POSTALCODE: ", end="\r\n", file=file_descriptor)
                print("ADDRESS-COUNTRY: ", end="\r\n", file=file_descriptor)
                print("EMAIL: ", end="\r\n", file=file_descriptor)
                for contact in log:
                    (
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
                        freq = self.fakefreq(band, mode)
                    print(
                        f"QSO: {freq.rjust(6)} {mode} {loggeddate} {loggedtime} "
                        f"{self.preference['mycall']} {self.preference['myclass']} "
                        f"{self.preference['mysection']} {hiscall} "
                        f"{hisclass} {hissection}",
                        end="\r\n",
                        file=file_descriptor,
                    )
                print("END-OF-LOG:", end="\r\n", file=file_descriptor)
        except IOError as exception:
            logger.critical(
                "cabrillo: IO error: %s, writing to %s", exception, filename
            )
            self.infobox.insertPlainText(" Failed\n\n")
            app.processEvents()
            return
        self.infobox.insertPlainText(" Done\n\n")
        app.processEvents()

    def generate_logs(self):
        """Do this when generate logs button pressed"""
        self.infobox.clear()
        self.show_dirty_records()
        self.resolve_dirty_records()
        self.cabrillo()
        self.generate_band_mode_tally()
        self.adif()
        if self.connect_to_server:
            update = {
                "cmd": "LOG",
                "station": self.preference.get("mycall", ""),
            }
            bytesToSend = bytes(dumps(update), encoding="ascii")
            try:
                self.server_udp.sendto(
                    bytesToSend, (self.multicast_group, int(self.multicast_port))
                )
            except OSError as err:
                logger.warning("%s", err)


class EditQSODialog(QtWidgets.QDialog):
    """Edit QSO Dialog"""

    theitem = ""
    database = None

    def __init__(self, parent=None):
        """initialize dialog"""
        super().__init__(parent)
        self.working_path = os.path.dirname(__loader__.get_filename())
        data_path = self.working_path + "/data/dialog.ui"
        uic.loadUi(data_path, self)
        self.deleteButton.clicked.connect(self.delete_contact)
        self.buttonBox.accepted.connect(self.save_changes)
        self.change = QsoEdit()
        self.unique_id = None

    def set_up(self, linetopass, thedatabase):
        """Set up variables"""
        (
            self.theitem,
            thecall,
            theclass,
            thesection,
            thedate,
            thetime,
            thefreq,
            theband,
            themode,
            thepower,
        ) = linetopass.split()
        self.editCallsign.setText(thecall)
        self.editClass.setText(theclass)
        self.editSection.setText(thesection)
        self.editFreq.setText(thefreq)
        self.editBand.setCurrentIndex(self.editBand.findText(theband.replace("M", "")))
        self.editMode.setCurrentIndex(self.editMode.findText(themode))
        self.editPower.setValue(int(thepower[: len(thepower) - 1]))
        date_time = thedate + " " + thetime
        now = QtCore.QDateTime.fromString(date_time, "yyyy-MM-dd hh:mm:ss")
        self.editDateTime.setDateTime(now)
        self.database = thedatabase
        self.unique_id = self.database.get_unique_id(self.theitem)

    def save_changes(self):
        """Save update to db"""
        qso = [
            self.editCallsign.text().upper(),
            self.editClass.text().upper(),
            self.editSection.text().upper(),
            self.editDateTime.text(),
            self.editBand.currentText(),
            self.editMode.currentText().upper(),
            self.editPower.value(),
            self.editFreq.text(),
            self.theitem,
        ]
        self.database.change_contact(qso)
        if window.connect_to_server:
            stale = datetime.now() + timedelta(seconds=30)
            command = {"cmd": "UPDATE"}
            command["hiscall"] = self.editCallsign.text().upper()
            command["class"] = self.editClass.text().upper()
            command["section"] = self.editSection.text().upper()
            command["date_time"] = self.editDateTime.text()
            command["frequency"] = self.editFreq.text()
            command["band"] = self.editBand.currentText()
            command["mode"] = self.editMode.currentText().upper()
            command["power"] = self.editPower.value()
            command["station"] = window.preference["mycall"].upper()
            command["unique_id"] = self.unique_id
            command["expire"] = stale.isoformat()
            window.server_commands.append(command)
            bytesToSend = bytes(dumps(command), encoding="ascii")
            try:
                window.server_udp.sendto(
                    bytesToSend, (window.multicast_group, int(window.multicast_port))
                )
            except OSError as err:
                logger.warning("%s", err)

        if window.preference.get("send_n1mm_packets"):
            window.n1mm.contact_info["rxfreq"] = self.editFreq.text()[:-1]
            window.n1mm.contact_info["txfreq"] = self.editFreq.text()[:-1]
            window.n1mm.contact_info["mode"] = self.editMode.currentText().upper()
            window.n1mm.contact_info["band"] = self.editBand.currentText()
            window.n1mm.contact_info["mycall"] = window.preference.get("mycall")
            window.n1mm.contact_info["IsRunQSO"] = self.contact.get("IsRunQSO")
            window.n1mm.contact_info["timestamp"] = self.contact.get("date_time")
            window.n1mm.contact_info["call"] = self.editCallsign.text().upper()
            window.n1mm.contact_info["gridsquare"] = self.contact.get("grid")
            window.n1mm.contact_info["exchange1"] = self.editClass.text().upper()
            window.n1mm.contact_info["section"] = self.editSection.text().upper()
            window.n1mm.contact_info["name"] = self.contact.get("opname")
            window.n1mm.contact_info["power"] = self.editPower.value()
            window.n1mm.contact_info["ID"] = self.contact.get("unique_id")
            if window.n1mm.contact_info["mode"] in ("CW", "DG"):
                window.n1mm.contact_info["points"] = "2"
            else:
                window.n1mm.contact_info["points"] = "1"
            window.n1mm.send_contactreplace()

        self.change.lineChanged.emit()

    def delete_contact(self):
        """delete the contact"""
        oldguy = self.database.contact_by_id(self.theitem)
        self.database.delete_contact(self.theitem)
        if window.connect_to_server:
            stale = datetime.now() + timedelta(seconds=30)
            command = {}
            command["cmd"] = "DELETE"
            command["unique_id"] = self.unique_id
            command["station"] = window.preference["mycall"].upper()
            command["expire"] = stale.isoformat()
            window.server_commands.append(command)
            bytesToSend = bytes(dumps(command), encoding="ascii")
            try:
                window.server_udp.sendto(
                    bytesToSend, (window.multicast_group, int(window.multicast_port))
                )
            except OSError as err:
                logger.warning("%s", err)

        if window.preference.get("send_n1mm_packets"):
            window.n1mm.contactdelete["timestamp"] = datetime.now(
                dt.timezone.utc
            ).strftime("%Y-%m-%d %H:%M:%S")
            window.n1mm.contactdelete["call"] = oldguy[0][1]
            window.n1mm.contactdelete["ID"] = self.unique_id
            window.n1mm.send_contact_delete()

        self.change.lineChanged.emit()
        self.close()  # try:


class StartUp(QtWidgets.QDialog):
    """StartUp dialog"""

    def __init__(self, parent=None):
        """initialize dialog"""
        super().__init__(parent)
        self.working_path = os.path.dirname(__loader__.get_filename())
        data_path = self.working_path + "/data/startup.ui"
        uic.loadUi(data_path, self)
        self.continue_pushButton.clicked.connect(self.store)

    def set_call_sign(self, callsign):
        """populate callsign field"""
        self.dialog_callsign.setText(callsign)

    def set_class(self, myclass):
        """populate class field"""
        self.dialog_class.setText(myclass)

    def set_section(self, mysection):
        """populate section field"""
        self.dialog_section.setText(mysection)

    def get_callsign(self):
        """return callisgn text"""
        return self.dialog_callsign.text()

    def get_class(self):
        """return class text"""
        return self.dialog_class.text()

    def get_section(self):
        """return section text"""
        return self.dialog_section.text()

    def store(self):
        """store info"""
        self.accept()


def startup_dialog_finished():
    """get changes and close dialog"""
    window.mycallEntry.setText(startupdialog.get_callsign())
    window.changemycall()
    window.myclassEntry.setText(startupdialog.get_class())
    window.changemyclass()
    window.mysectionEntry.setText(startupdialog.get_section())
    window.changemysection()
    startupdialog.close()


logger = logging.getLogger("__name__")
handler = logging.StreamHandler()
formatter = logging.Formatter(
    datefmt="%H:%M:%S",
    fmt="[%(asctime)s] %(levelname)s %(module)s - %(funcName)s Line %(lineno)d:\n%(message)s",
)
handler.setFormatter(formatter)
logger.addHandler(handler)

if Path("./debug").exists():
    # if True:
    logger.setLevel(logging.DEBUG)
    print("debugging on")
else:
    print("debugging off")
    logger.setLevel(logging.WARNING)

app = QtWidgets.QApplication(sys.argv)
app.setStyle("Fusion")
working_path = os.path.dirname(__loader__.get_filename())
font_path = working_path + "/data"
families = load_fonts_from_dir(os.fspath(font_path))
window = MainWindow()
window.setWindowTitle(f"K6GTE Field Day Logger v{__version__}")
window.show()
window.read_cw_macros()
window.changeband()
window.changemode()
if window.preference["mycall"] != "":
    thethread = threading.Thread(
        target=window.lookupmygrid,
        daemon=True,
    )
    thethread.start()
if (
    window.preference["mycall"] == ""
    or window.preference["myclass"] == ""
    or window.preference["mysection"] == ""
):
    startupdialog = StartUp()
    startupdialog.accepted.connect(startup_dialog_finished)
    startupdialog.open()
    startupdialog.set_call_sign(window.preference["mycall"])
    startupdialog.set_class(window.preference["myclass"])
    startupdialog.set_section(window.preference["mysection"])
window.cloudlogauth()
window.stats()
window.read_sections()
window.read_scp()
window.logwindow()
window.sections()
window.callsign_entry.setFocus()

timer = QtCore.QTimer()
timer.timeout.connect(window.update_time)

timer2 = QtCore.QTimer()
timer2.timeout.connect(window.check_udp_queue)

timer3 = QtCore.QTimer()
timer3.timeout.connect(window.send_status_udp)


def run():
    """Main Entry"""
    PATH = os.path.dirname(__loader__.get_filename())
    if sys.platform == "linux":
        os.system(
            "xdg-icon-resource install --size 64 --context apps --mode user "
            f"{PATH}/icon/k6gte-fdlogger.png k6gte-fdlogger"
        )
        os.system(f"xdg-desktop-menu install {PATH}/data/k6gte-fieldday.desktop")
    timer.start(1000)
    timer2.start(1000)
    timer3.start(15000)
    sys.exit(app.exec())
    # app.exec()


if __name__ == "__main__":
    run()

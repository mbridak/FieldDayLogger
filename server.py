#!/usr/bin/env python3
"""This is the description"""

import logging
import socket
import time
import os
import threading

from json import JSONDecodeError, loads
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
            "%(funcName)s Line %(lineno)d:\n%(message)s"
        ),
        datefmt="%H:%M:%S",
        level=logging.DEBUG,
    )
    logging.debug("Debug started")
else:
    logging.basicConfig(level=logging.CRITICAL)

DB = DataBase("server_database.db")

MULTICAST_PORT = 2239
MULTICAST_GROUP = "224.1.1.1"
INTERFACE_IP = "0.0.0.0"

OURCALL = "XXXX"
OURCLASS = "XX"
OURSECTION = "XXX"
ALTPOWER = 0

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

print(
    f"Field Day aggregation server v{__version__}\n\n"
    f"          Network information\n"
    f"Multicast Group: {MULTICAST_GROUP}\n"
    f"Multicast Port:  {MULTICAST_PORT}\n"
    f"Interface IP:    {INTERFACE_IP}\n\n"
    f"           Group Information\n"
    f"Call:     {OURCALL}\n"
    f"Class:    {OURCLASS}\n"
    f"Section:  {OURSECTION}\n"
    f"AltPower: {bool(ALTPOWER)}\n"
)


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

while 1:
    try:
        payload = s.recv(1500)
        json_data = loads(payload.decode())
        timestamp = time.time()

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
            print(
                f"[{timestamp}] New Contact {json_data.get('station')}: {json_data.get('hiscall')} "
                f"{json_data.get('band')}M {json_data.get('mode')}"
            )
            continue

        if json_data.get("cmd") == "GET":
            print(f"[{timestamp}] {json_data}\n")
            continue

        if json_data.get("cmd") == "DELETE":
            print(f"[{timestamp}] Deleting: {json_data.get('unique_id')}")
            DB.delete_contact(json_data.get("unique_id"))
            continue

        if json_data.get("cmd") == "UPDATE":
            print(
                f"[{timestamp}] Updating {json_data.get('unique_id')} {json_data.get('hiscall')} "
                f"{json_data.get('band')} {json_data.get('mode')}"
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
            continue

        if json_data.get("cmd") == "PING":
            if not json_data.get("host"):
                print(
                    f"[{timestamp}] Ping: {json_data.get('station')} "
                    f"{json_data.get('band')}M {json_data.get('band')}"
                )
            if json_data.get("station"):
                people[
                    json_data.get("station")
                ] = f"{json_data.get('band')} {json_data.get('mode')}"
                print(people)
            continue

    except UnicodeDecodeError as err:
        print(f"[{timestamp}] Not JSON: {err}\n{payload}\n")
    except JSONDecodeError as err:
        print(f"[{timestamp}] Not JSON: {err}\n{payload}\n")

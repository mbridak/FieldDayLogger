#!/usr/bin/env python3
"""This is the description"""

import logging
import socket
import time
import threading

from json import JSONDecodeError, dumps, loads
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


def send_pulse():
    """send heartbeat"""
    while True:
        pulse = b'{\n    "cmd": "PING",\n    "host": "server"\n}'
        s.sendto(pulse, (MULTICAST_GROUP, MULTICAST_PORT))
        time.sleep(1)


DB = DataBase("server_database.db")

MULTICAST_PORT = 2239
MULTICAST_GROUP = "224.1.1.1"
INTERFACE_IP = "0.0.0.0"

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
        if payload == b"Alive":
            continue
        json_data = loads(payload.decode())
        timestamp = time.time()

        if json_data.get("cmd") == "POST":

            print(f"[{timestamp}] {json_data}\n")

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

        if json_data.get("cmd") == "GET":
            print(f"[{timestamp}] {json_data}\n")

        if json_data.get("cmd") == "DELETE":
            print(f"[{timestamp}] {json_data}\n")
            DB.delete_contact(json_data.get("unique_id"))

        if json_data.get("cmd") == "UPDATE":
            print(f"[{timestamp}] {json_data}\n")
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
                    json_data.get("unique_id"),
                )
            )

        if json_data.get("cmd") == "PING":
            print(f"[{timestamp}] {json_data}\n")
            if json_data.get("call"):
                people[
                    json_data.get("call")
                ] = f"{json_data.get('band')} {json_data.get('mode')}"
                print(people)

    except UnicodeDecodeError as err:
        print(f"Not JSON: {err}\n{payload}\n")
    except JSONDecodeError as err:
        print(f"Not JSON: {err}\n{payload}\n")

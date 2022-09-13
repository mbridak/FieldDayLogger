#!/usr/bin/env python3
"""Test multicasting"""
# pylint: disable=invalid-name
# pylint: disable=line-too-long
import socket
import time
import uuid
from json import dumps, loads


def main():
    """Wee"""
    MULTICAST_GROUP = "224.1.1.1"
    MULTICAST_PORT = 2239

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    while True:
        preference = {
            "cmd": "POST",
            "hiscall": "K5TUX",
            "section": "ORG",
            "class": "1E",
            "mode": "CW",
            "band": "20",
            "frequency": "14032000",
            "power": "10",
            "grid": "DM13at",
            "opname": "Jim",
            "station": "K6GTE",
        }
        preference["unique_id"] = uuid.uuid4().hex
        bytesToSend = bytes(dumps(preference, indent=4), encoding="ascii")
        sock.sendto(bytesToSend, (MULTICAST_GROUP, MULTICAST_PORT))

        preference["unique_id"] = "8f73b3fce277473eaf2c923ff4e6a15e"
        preference["cmd"] = "DELETE"
        bytesToSend = bytes(dumps(preference, indent=4), encoding="ascii")
        sock.sendto(bytesToSend, (MULTICAST_GROUP, MULTICAST_PORT))
        time.sleep(1)

        preference = {
            "cmd": "UPDATE",
            "hiscall": "KM6HQI",
            "section": "WWA",
            "class": "12A",
            "mode": "CW",
            "band": "40",
            "frequency": "14032000",
            "power": "5",
            "grid": "XX13at",
            "opname": "BOB",
            "station": "K6GTE",
            "date_time": "2022-08-02 21:37:14",
        }
        preference["unique_id"] = "a4819bae797e4d60839c94dcae85a38d"
        bytesToSend = bytes(dumps(preference, indent=4), encoding="ascii")
        sock.sendto(bytesToSend, (MULTICAST_GROUP, MULTICAST_PORT))

        preference = {
            "cmd": "PING",
            "call": "K6GTE",
            "band": "20",
            "mode": "CW",
        }
        bytesToSend = bytes(dumps(preference, indent=4), encoding="ascii")
        sock.sendto(bytesToSend, (MULTICAST_GROUP, MULTICAST_PORT))

        preference = {
            "cmd": "PING",
            "call": "N6QW",
            "band": "20",
            "mode": "PH",
        }
        bytesToSend = bytes(dumps(preference, indent=4), encoding="ascii")
        sock.sendto(bytesToSend, (MULTICAST_GROUP, MULTICAST_PORT))

        preference = {
            "cmd": "PING",
            "call": "K6GTE",
            "band": "40",
            "mode": "CW",
        }
        bytesToSend = bytes(dumps(preference, indent=4), encoding="ascii")
        sock.sendto(bytesToSend, (MULTICAST_GROUP, MULTICAST_PORT))

        break


if __name__ == "__main__":
    main()

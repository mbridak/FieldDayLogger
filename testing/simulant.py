#!/usr/bin/env python3
"""Simulated Field Day club participant"""

import random
import socket
import uuid
import time
from datetime import datetime
from json import dumps, loads, JSONDecodeError

MULTICAST_PORT = 2239
MULTICAST_GROUP = "224.1.1.1"
INTERFACE_IP = "0.0.0.0"
MODE = "CW"
BAND = "20"
POWER = 5


def generate_class():
    """Generates a valid Field Day class"""
    suffix = ["A", "B", "C", "D", "E", "F"][random.randint(0, 5)]
    if "C" in suffix:
        return "1C"
    if "D" in suffix:
        return "1D"
    if "E" in suffix:
        return "1E"
    if "B" in suffix:
        return str(random.randint(1, 2)) + suffix
    if "A" in suffix:
        return str(random.randint(3, 20)) + suffix

    return str(random.randint(1, 20)) + suffix


def generate_callsign():
    """Generates a US callsign, Need to add the land of maple syrup."""
    prefix = ["A", "K", "N", "W"]
    letters = [
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I",
        "J",
        "K",
        "L",
        "M",
        "N",
        "O",
        "P",
        "Q",
        "R",
        "S",
        "T",
        "U",
        "V",
        "W",
        "X",
        "Y",
        "Z",
    ]
    callsign = prefix[random.randint(0, 3)]

    add_second_prefix_letter = random.randint(0, 2) == 0
    if "A" in callsign:  # We have no choice. Must add second prefix.
        callsign += letters[random.randint(0, 11)]
        add_second_prefix_letter = False

    if add_second_prefix_letter:
        callsign += letters[random.randint(0, 25)]

    callsign += str(random.randint(0, 9))
    if "A" in callsign[0]:
        suffix_length = random.randint(1, 2)
    else:
        length = [
            1,
            2,
            2,
            3,
            3,
            3,
        ]  # Stupid way to get a weighted result. But I'm stupid so it's normal.
        suffix_length = length[random.randint(0, 5)]

    for unused_variable in range(suffix_length):
        callsign += letters[random.randint(0, 25)]

    return callsign


def generate_section(call):
    """Generate section based on call region"""
    call_areas = {
        "0": "CO MO IA ND KS NE MN SD",
        "1": "CT RI EMA VT ME WMA NH",
        "2": "ENY NNY NLI SNJ NNJ WNY",
        "3": "DE MDC EPA WPA",
        "4": "AL SC GA SFL KY TN NC VA NFL VI PR WCF",
        "5": "AR NTX LA OK MS STX NM WTX",
        "6": "EBA SCV LAX SDG ORG SF PAC SJV SB SV",
        "7": "AK NV AZ OR EWA UT ID WWA MT WY",
        "8": "MI WV OH",
        "9": "IL WI IN",
    }
    if call[1].isdigit():
        area = call[1]
    else:
        area = call[2]
    sections = call_areas[area].split()
    return sections[random.randint(0, len(sections) - 1)]


def fakefreq(band, mode):
    """
    If unable to obtain a frequency from the rig,
    This will return a sane value for a frequency mainly for the cabrillo and adif log.
    Takes a band and mode as input and returns freq in khz.
    """
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
    return freqtoreturn


def log_contact():
    """Send a contgact to the server."""
    unique_id = uuid.uuid4().hex
    callsign = generate_callsign()
    contact = {
        "cmd": "POST",
        "hiscall": callsign,
        "class": generate_class(),
        "section": generate_section(callsign),
        "mode": MODE,
        "band": BAND,
        "frequency": int(float(fakefreq(BAND, MODE)) * 1000),
        "power": POWER,
        "grid": "DM13at",
        "opname": "John Doe",
        "station": STATION_CALL,
        "unique_id": unique_id,
    }
    # self.server_commands.append(contact)
    bytesToSend = bytes(dumps(contact, indent=4), encoding="ascii")
    try:
        s.sendto(bytesToSend, (MULTICAST_GROUP, int(MULTICAST_PORT)))
    except OSError as err:
        print(f"Error: {err}")
        # logging.warning("%s", err)


def send_status_udp():
    """Send status update to server informing of our band and mode"""

    # if self.groupcall is None and self.preference["mycall"] != "":
    #     self.query_group()
    #     return

    update = {
        "cmd": "PING",
        "mode": MODE,
        "band": BAND,
        "station": STATION_CALL,
    }
    bytesToSend = bytes(dumps(update), encoding="ascii")
    try:
        s.sendto(bytesToSend, (MULTICAST_GROUP, int(MULTICAST_PORT)))
    except OSError as err:
        print(f"Error: {err}")
        # logging.warning("%s", err)


s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("", MULTICAST_PORT))
mreq = socket.inet_aton(MULTICAST_GROUP) + socket.inet_aton(INTERFACE_IP)
s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, bytes(mreq))


STATION_CALL = generate_callsign()


def main():
    """The main loop"""
    send_status_udp()
    while True:
        log_contact()
        time.sleep(1)


if __name__ == "__main__":
    main()

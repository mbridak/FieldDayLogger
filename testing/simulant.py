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

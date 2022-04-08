#!/usr/bin/env python3
"""Test multicasting"""
# pylint: disable=invalid-name
import socket
import time


def main():
    """Wee"""
    bytesToSend = b"\xad\xbc\xcb\xda\x00\x00\x00\x02\x00\x00\x00\x0c\x00\x00\x00\x06WSJT-X\x00\x00\x01l\n<adif_ver:5>3.1.0\n<programid:6>WSJT-X\n<EOH>\n<call:5>KE0OG <gridsquare:6>DM10AT <mode:3>FT8 <rst_sent:0> <rst_rcvd:0> <qso_date:8>20210329 <time_on:6>183213 <qso_date_off:8>20210329 <time_off:6>183213 <band:3>20m <freq:9>14.074754 <station_callsign:5>K6GTE <my_gridsquare:6>DM13AT <contest_id:14>ARRL-FIELD-DAY <SRX_STRING:5>1D UT <class:2>1D <arrl_sect:2>UT <EOR>"
    # bytesToSend = bytes("Hello", encoding="ascii")
    MULTICAST_GROUP = "224.1.1.1"
    MULTICAST_PORT = 2237

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    while True:
        sock.sendto(bytesToSend, (MULTICAST_GROUP, MULTICAST_PORT))
        time.sleep(1)


if __name__ == "__main__":
    main()

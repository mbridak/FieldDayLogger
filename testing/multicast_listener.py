#!/usr/bin/env python3
"""Test multicasting"""
# pylint: disable=invalid-name
import socket
import time

multicast_port = 2237
multicast_group = "224.1.1.1"
interface_ip = "0.0.0.0"

s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
s.bind(("", multicast_port))
mreq = socket.inet_aton(multicast_group) + socket.inet_aton(interface_ip)
s.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, bytes(mreq))

while 1:
    print(f"[{time.time()}] {s.recv(1500)}")

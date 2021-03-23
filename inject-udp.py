#!/usr/bin/env python3
import socket

msgFromClient       = "<CALL:7>W1TEST3 <GRIDSQUARE:6>DM13AT <MODE:3>FT8 <RST_SENT:0> <RST_RCVD:0> <QSO_DATE:8>20210323 <TIME_ON:6>194651 <QSO_DATE_OFF:8>20210323 <TIME_OFF:6>194651 <BAND:3>20m <FREQ:9>14.075500 <STATION_CALLSIGN:0> <MY_GRIDSQUARE:0> <CONTEST_ID:14>ARRL-FIELD-DAY <SRX_STRING:6>3A NFL <CLASS:2>3A <ARRL_SECT:3>NFL <DXCC:3>291 <COUNTRY:13>United States <EOR>"
bytesToSend         = str.encode(msgFromClient)
serverAddressPort   = ("127.0.0.1", 2333)
bufferSize          = 1024

# Create a UDP socket at client side
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Send to server using created UDP socket
UDPClientSocket.sendto(bytesToSend, serverAddressPort)

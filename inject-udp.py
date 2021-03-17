#!/usr/bin/env python3
import socket

msgFromClient       = "<command:3>Log <parameters:146> <Band:3>20M <Call:5>M4HXM <Freq:6>14.076 <Mode:3>FT8 <QSO_DATE:8>20210626 <TIME_ON:6>184000 <RST_Rcvd:3>-03 <RST_Sent:3>-07 <TX_PWR:3>5.0 <STX:6>1B ORG <SRX:6>1D SJV <GRIDSQUARE:6>DM13at <EOR>"
bytesToSend         = str.encode(msgFromClient)
serverAddressPort   = ("127.0.0.1", 2333)
bufferSize          = 1024

# Create a UDP socket at client side
UDPClientSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Send to server using created UDP socket
UDPClientSocket.sendto(bytesToSend, serverAddressPort)
msgFromServer = UDPClientSocket.recvfrom(bufferSize)

msg = "Message from Server {}".format(msgFromServer[0])
print(msg)

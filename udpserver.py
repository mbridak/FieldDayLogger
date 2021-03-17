#!/usr/bin/env python3
import socket
import sqlite3
from sqlite3 import Error

database = "FieldDay.db"
localIP     = "127.0.0.1"
localPort   = 2333
bufferSize  = 1024
datadict = {}

def getvalue(item):
    if item in datadict:
        return datadict[item]
    return 'NOT_FOUND'

msgFromServer       = "Got it."
bytesToSend         = str.encode(msgFromServer)

# Create a datagram socket
UDPServerSocket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)

# Bind to address and ip
UDPServerSocket.bind((localIP, localPort))
print("UDP server up and listening")

# Listen for incoming datagrams
while(True):
    bytesAddressPair = UDPServerSocket.recvfrom(bufferSize)
    message = bytesAddressPair[0]
    address = bytesAddressPair[1]

    data = message.decode()
    clientIP  = f"Client IP Address: {address}"
    splitdata = data.upper().split("<")

    for x in splitdata:
        if x:
            a = x.split(":")
            if a==['EOR>']: break
            datadict[a[0]] = a[1].split(">")[1].strip()

    x = getvalue("COMMAND")
    if x == "LOG":
        call = getvalue("CALL")
        dayt = getvalue("QSO_DATE")
        tyme = getvalue("TIME_ON")
        dt = f"{dayt[0:4]}-{dayt[4:6]}-{dayt[6:8]} {tyme[0:2]}:{tyme[2:4]}:{tyme[4:6]}"
        freq = int(float(getvalue("FREQ"))*1000000)
        band = getvalue("BAND").split("M")[0]
        grid = getvalue("GRIDSQUARE")
        name = getvalue("NAME")
        hisclass, hissect = getvalue("SRX").split(' ')
        power = int(float(getvalue("TX_PWR")))

        contact = (call, hisclass, hissect, dt, freq, band, "DI", power, grid, name)
        try:
            conn = sqlite3.connect(database)
            sql = "INSERT INTO contacts(callsign, class, section, date_time, frequency, band, mode, power, grid, opname) VALUES(?,?,?,?,?,?,?,?,?,?)"
            cur = conn.cursor()
            cur.execute(sql, contact)
            conn.commit()
        except Error as e:
            print("Log Contact: ")
            print(e)
        finally:
            conn.close()


        print(f'CALL: {getvalue("CALL")}')
        print(f'QSO_DATE: {getvalue("QSO_DATE")}')
        print(f'TIME_ON: {getvalue("TIME_ON")}')
        print(f'CONTEST_ID: {getvalue("CONTEST_ID")}')
        print(f'MODE: {getvalue("MODE")}')
        print(f'FREQ: {getvalue("FREQ")}')
        print(f'FREQ_RX: {getvalue("FREQ_RX")}')
        print(f'BAND: {getvalue("BAND")}')
        print(f'COMMENT: {getvalue("COMMENT")}')
        print(f'CQZ: {getvalue("CQZ")}')
        print(f'ITUZ: {getvalue("ITUZ")}')
        print(f'GRIDSQUARE: {getvalue("GRIDSQUARE")}')
        print(f'NAME: {getvalue("NAME")}')
        print(f'RST_RCVD: {getvalue("RST_RCVD")}')
        print(f'RST_SENT: {getvalue("RST_SENT")}')
        print(f'TX_PWR: {getvalue("TX_PWR")}')
        print(f'RX_PWR: {getvalue("RX_PWR")}')
        print(f'SRX: {getvalue("SRX")}')
        print(f'STX: {getvalue("STX")}')
        print(f'QTH: {getvalue("QTH")}')
        print(f'OPERATOR: {getvalue("OPERATOR")}')
        print(f'RADIO_NR: {getvalue("RADIO_NR")}')
        print(f'POINTS: {getvalue("POINTS")}')
        print(f'ARI_PROV: {getvalue("ARI_PROV")}')
        print(f'ARRL_SECT: {getvalue("ARRL_SECT")}')
        print(f'DIG: {getvalue("DIG")}')
        print(f'DISTRIKT: {getvalue("DISTRIKT")}')
        print(f'DOK: {getvalue("DOK")}')
        print(f'IOTA: {getvalue("IOTA")}')
        print(f'KDA: {getvalue("KDA")}')
        print(f'OBLAST: {getvalue("OBLAST")}')
        print(f'PFX: {getvalue("PFX")}')
        print(f'RDA: {getvalue("RDA")}')
        print(f'SAC: {getvalue("SAC")}')
        print(f'SECT: {getvalue("SECT")}')
        print(f'STATE: {getvalue("STATE")}')
        print(f'IARU_ZONE: {getvalue("IARU_ZONE")}')
        print(f'SECTION: {getvalue("SECTION")}')
        print(f'NAQSO_SECT: {getvalue("NAQSO_SECT")}')
        print(f'VE_PROV: {getvalue("VE_PROV")}')
        print(f'UKEI: {getvalue("UKEI")}')
        print(f'WWPMC: {getvalue("WWPMC")}')
        print(f'PRECEDENCE: {getvalue("PRECEDENCE")}')
        print(f'CHECK: {getvalue("CHECK")}')

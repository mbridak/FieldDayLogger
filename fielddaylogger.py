#!/usr/bin/env python3

#Nothing to see here move along.
#xplanet -body earth -window -longitude -117 -latitude 38 -config Default -projection azmithal -radius 200 -wait 5

import json
import requests
import sys
import time
import sqlite3
import socket
import os

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5 import uic
from datetime import datetime
from sqlite3 import Error
from pathlib import Path

class MainWindow(QtWidgets.QMainWindow):
	database = "FieldDay.db"
	mycall = ""
	myclass = ""
	mysection = ""
	power = "0"
	band = "40"
	mode = "CW"
	qrp = False
	highpower = False
	bandmodemult = 0
	altpower = False
	outdoors = False
	notathome = False
	satellite = False
	cwcontacts = "0"
	phonecontacts = "0"
	digitalcontacts = "0"
	score=0
	secPartial = {}
	secName = {}
	secState = {}
	scp=[]
	wrkdsections=[]
	linetopass=""
	bands = ('160', '80', '60','40', '20', '15', '10', '6', '2')
	dfreq = {'160':"1.830", '80':"3.530", '60':"53.300", '40':"7.030", '20':"14.030", '15':"21.030", '10':"28.030", '6':"50.030", '2':"144.030", '222':"222.030", '432':"432.030", 'SAT':"0.0"}
	cloudlogapi = ""
	cloudlogurl = ""
	cloudlogauthenticated = False
	usecloudlog = False
	qrzurl = ""
	qrzpass = ""
	qrzname = ""
	useqrz = False
	usehamdb = False
	qrzsession = False
	rigctrlsocket = ""
	rigctrlhost = ""
	rigctrlport = ""
	rigonline = False
	userigctl = False
	markerfile = ".xplanet/markers/ham"
	usemarker = False
	oldfreq = 0
	oldmode = 0
	basescore = 0
	powermult = 0


	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		uic.loadUi(self.relpath("main.ui"), self)
		self.listWidget.itemDoubleClicked.connect(self.qsoclicked)
		self.callsign_entry.textEdited.connect(self.calltest)
		self.class_entry.textEdited.connect(self.classtest)
		self.section_entry.textEdited.connect(self.sectiontest)
		self.callsign_entry.returnPressed.connect(self.log_contact)
		self.class_entry.returnPressed.connect(self.log_contact)
		self.section_entry.returnPressed.connect(self.log_contact)
		self.mycallEntry.textEdited.connect(self.changemycall)
		self.myclassEntry.textEdited.connect(self.changemyclass)
		self.mysectionEntry.textEdited.connect(self.changemysection)
		self.band_selector.activated.connect(self.changeband)
		self.mode_selector.activated.connect(self.changemode)
		self.power_selector.valueChanged.connect(self.changepower)
		self.callsign_entry.editingFinished.connect(self.dupCheck)
		self.section_entry.textEdited.connect(self.sectionCheck)
		self.genLogButton.clicked.connect(self.generateLogs)
		self.radio_icon.setPixmap(QtGui.QPixmap(self.relpath('icon/radio_grey.png')))
		self.cloudlog_icon.setPixmap(QtGui.QPixmap(self.relpath('icon/cloud_grey.png')))
		self.QRZ_icon.setStyleSheet("color: rgb(136, 138, 133);")
		self.settingsbutton.clicked.connect(self.settingspressed)
		self.radiochecktimer = QtCore.QTimer()
		self.radiochecktimer.timeout.connect(self.Radio)
		self.radiochecktimer.start(1000)

	def relpath(self, filename):
		"""
		This is used if run as a pyinstaller packaged application.
		So the app can find the temp files.
		"""
		try:
			base_path = sys._MEIPASS # pylint: disable=no-member
		except:
			base_path = os.path.abspath(".")
		return os.path.join(base_path, filename)
		
	def settingspressed(self):
		settingsdialog = settings(self)
		settingsdialog.exec()
		self.infobox.clear()
		self.readpreferences()
		self.qrzauth()
		self.cloudlogauth()

	def has_internet(self):
		try:
			socket.create_connection(("1.1.1.1", 53))
			return True
		except OSError:
			pass
		return False

	def qrzauth(self):
		if self.useqrz and self.has_internet():
			try:
				payload = {'username':self.qrzname, 'password':self.qrzpass}
				r=requests.get(self.qrzurl,params=payload, timeout=1.0)
				if r.status_code == 200 and r.text.find('<Key>') > 0:
					self.qrzsession=r.text[r.text.find('<Key>')+5:r.text.find('</Key>')]
					self.QRZ_icon.setStyleSheet("color: rgb(128, 128, 0);")
				else:
					self.qrzsession = False
					self.QRZ_icon.setStyleSheet("color: rgb(136, 138, 133);")
				if r.status_code == 200 and r.text.find('<Error>') > 0:
					errorText = r.text[r.text.find('<Error>')+7:r.text.find('</Error>')]
					self.infobox.insertPlainText("\nQRZ Error: "+ errorText + "\n")
			except requests.exceptions.RequestException as e:
				self.infobox.insertPlainText(f"****QRZ Error****\n{e}\n")
		else:
			self.QRZ_icon.setStyleSheet("color: rgb(26, 26, 26);")
			self.qrzsession = False

	def cloudlogauth(self):
		self.cloudlog_icon.setPixmap(QtGui.QPixmap(self.relpath('icon/cloud_grey.png')))
		self.cloudlogauthenticated = False
		if self.usecloudlog:
			try:
				self.cloudlog_icon.setPixmap(QtGui.QPixmap(self.relpath('icon/cloud_red.png')))
				test = self.cloudlogurl[:-3]+"auth/"+self.cloudlogapi
				r=requests.get(test,params={}, timeout=2.0)
				if r.status_code == 200 and r.text.find('<status>') > 0:
					if r.text[r.text.find('<status>')+8:r.text.find('</status>')] == "Valid":
						self.cloudlogauthenticated = True
						self.cloudlog_icon.setPixmap(QtGui.QPixmap(self.relpath('icon/cloud_green.png')))
			except requests.exceptions.RequestException as e:
				self.infobox.insertPlainText(f"****Cloudlog Auth Error:****\n{e}\n")


	def getband(self, freq):
		if freq.isnumeric():
			frequency = int(float(freq))
			if frequency > 1800000 and frequency < 2000000:
				return "160"
			if frequency > 3500000 and frequency < 4000000:
				return "80"
			if frequency > 5330000 and frequency < 5406000:
				return "60"
			if frequency > 7000000 and frequency < 7300000:
				return "40"
			if frequency > 10100000 and frequency < 10150000:
				return "30"
			if frequency > 14000000 and frequency < 14350000:
				return "20"
			if frequency > 18068000 and frequency < 18168000:
				return "17"
			if frequency > 21000000 and frequency < 21450000:
				return "15"
			if frequency > 24890000 and frequency < 24990000:
				return "12"
			if frequency > 28000000 and frequency < 29700000:
				return "10"
			if frequency > 50000000 and frequency < 54000000:
				return "6"
			if frequency > 144000000 and frequency < 148000000:
				return "2"
		else:
			return "0"

	def getmode(self, rigmode):
		if rigmode == "CW" or rigmode == 'CWR':
			return "CW"
		if rigmode == "USB" or rigmode == "LSB" or rigmode == "FM" or rigmode == "AM":
			return "PH"
		return "DI" #All else digital

	def setband(self, theband):
		self.band_selector.setCurrentIndex(self.band_selector.findText(theband))
		self.changeband()

	def setmode(self, themode):
		self.mode_selector.setCurrentIndex(self.mode_selector.findText(themode))
		self.changemode()

	def pollRadio(self):
		if self.rigonline:
			try:
				self.rigctrlsocket.settimeout(0.5)
				self.rigctrlsocket.send(b'f\n')
				newfreq = self.rigctrlsocket.recv(1024).decode().strip()
				self.rigctrlsocket.send(b'm\n')
				newmode = self.rigctrlsocket.recv(1024).decode().strip().split()[0]
				self.radio_icon.setPixmap(QtGui.QPixmap(self.relpath('icon/radio_green.png')))
				if newfreq != self.oldfreq or newmode != self.oldmode:
					self.oldfreq = newfreq
					self.oldmode = newmode
					self.setband(str(self.getband(newfreq)))
					self.setmode(str(self.getmode(newmode)))
			except:
				self.rigonline = False
				self.radio_icon.setPixmap(QtGui.QPixmap(self.relpath('icon/radio_red.png')))

	def checkRadio(self):
		if self.userigctl:
			self.rigctrlsocket=socket.socket()
			self.rigctrlsocket.settimeout(0.1)
			self.rigonline = True
			try:
				self.rigctrlsocket.connect((self.rigctrlhost, int(self.rigctrlport)))
				self.radio_icon.setPixmap(QtGui.QPixmap(self.relpath('icon/radio_red.png')))
			except:
				self.rigonline = False
				self.radio_icon.setPixmap(QtGui.QPixmap(self.relpath('icon/radio_grey.png')))
		else:
			self.rigonline = False

	def Radio(self):
		self.checkRadio()
		self.pollRadio()

	def flash(self):
		self.setStyleSheet("background-color: rgb(245, 121, 0);\ncolor: rgb(211, 215, 207);")
		app.processEvents()
		self.setStyleSheet("background-color: rgb(42, 42, 42);\ncolor: rgb(211, 215, 207);")
		app.processEvents()

	def keyPressEvent(self, event):
		if(event.key() == 16777216): #ESC
			self.clearinputs()

	def clearinputs(self):
		self.callsign_entry.clear()
		self.class_entry.clear()
		self.section_entry.clear()
		self.callsign_entry.setFocus()

	def changeband(self):
		self.band = self.band_selector.currentText()

	def changemode(self):
		self.mode = self.mode_selector.currentText()

	def changepower(self):
		self.power = str(self.power_selector.value())
		self.writepreferences()

	def changemycall(self):
		text = self.mycallEntry.text()
		if(len(text)):
			if text[-1] == " ":
				self.mycallEntry.setText(text.strip())
			else:
				cleaned = ''.join(ch for ch in text if ch.isalnum() or ch=='/').upper()
				self.mycallEntry.setText(cleaned)
		self.mycall = self.mycallEntry.text()
		if self.mycall !="":
			self.mycallEntry.setStyleSheet("border: 1px solid green;")
		else:
			self.mycallEntry.setStyleSheet("border: 1px solid red;")
		self.writepreferences()

	def changemyclass(self):
		text = self.myclassEntry.text()
		if(len(text)):
			if text[-1] == " ":
				self.myclassEntry.setText(text.strip())
			else:
				cleaned = ''.join(ch for ch in text if ch.isalnum() or ch=='/').upper()
				self.myclassEntry.setText(cleaned)
		self.myclass = self.myclassEntry.text()
		if self.myclass != "":
			self.myclassEntry.setStyleSheet("border: 1px solid green;")
		else:
			self.myclassEntry.setStyleSheet("border: 1px solid red;")
		self.writepreferences()

	def changemysection(self):
		text = self.mysectionEntry.text()
		if(len(text)):
			if text[-1] == " ":
				self.mysectionEntry.setText(text.strip())
			else:
				cleaned = ''.join(ch for ch in text if ch.isalpha() or ch=='/').upper()
				self.mysectionEntry.setText(cleaned)
		self.mysection = self.mysectionEntry.text()
		if self.mysection != "":
			self.mysectionEntry.setStyleSheet("border: 1px solid green;")
		else:
			self.mysectionEntry.setStyleSheet("border: 1px solid red;")
		self.writepreferences()

	def calltest(self):
		text = self.callsign_entry.text()
		if(len(text)):
			if text[-1] == " ":
				self.callsign_entry.setText(text.strip())
				self.class_entry.setFocus()
			else:
				cleaned = ''.join(ch for ch in text if ch.isalnum() or ch=='/').upper()
				self.callsign_entry.setText(cleaned)
				self.superCheck()

	def classtest(self):
		text = self.class_entry.text()
		if(len(text)):
			if text[-1] == " ":
				self.class_entry.setText(text.strip())
				self.section_entry.setFocus()
			else:
				cleaned = ''.join(ch for ch in text if ch.isalnum()).upper()
				self.class_entry.setText(cleaned)

	def sectiontest(self):
		text = self.section_entry.text()
		if(len(text)):
			if text[-1] == " ":
				self.section_entry.setText(text.strip())
				self.callsign_entry.setFocus()
			else:
				cleaned = ''.join(ch for ch in text if ch.isalpha()).upper()
				self.section_entry.setText(cleaned)

	def create_DB(self):
		""" create a database and table if it does not exist """
		try:
			conn = sqlite3.connect(self.database)
			c = conn.cursor()
			sql_table = """ CREATE TABLE IF NOT EXISTS contacts (id INTEGER PRIMARY KEY, callsign text NOT NULL, class text NOT NULL, section text NOT NULL, date_time text NOT NULL, frequency INTEGER DEFAULT 0, band text NOT NULL, mode text NOT NULL, power INTEGER NOT NULL, grid text NOT NULL, opname text NOT NULL); """
			c.execute(sql_table)
			sql_table = """ CREATE TABLE IF NOT EXISTS preferences (id INTEGER PRIMARY KEY, mycallsign TEXT DEFAULT '', myclass TEXT DEFAULT '', mysection TEXT DEFAULT '', power TEXT DEFAULT '0', altpower INTEGER DEFAULT 0, outdoors INTEGER DEFAULT 0, notathome INTEGER DEFAULT 0, satellite INTEGER DEFAULT 0, qrzusername TEXT DEFAULT 'w1aw', qrzpassword TEXT default 'secret', qrzurl TEXT DEFAULT 'https://xmldata.qrz.com/xml/',cloudlogapi TEXT DEFAULT 'cl12345678901234567890', cloudlogurl TEXT DEFAULT 'http://www.yoururl.com/Cloudlog/index.php/api/qso', useqrz INTEGER DEFAULT 0, usecloudlog INTEGER DEFAULT 0, userigcontrol INTEGER DEFAULT 0, rigcontrolip TEXT DEFAULT '127.0.0.1', rigcontrolport TEXT DEFAULT '4532',markerfile TEXT default 'secret', usemarker INTEGER DEFAULT 0, usehamdb INTEGER DEFAULT 0); """
			c.execute(sql_table)
			conn.commit()
			conn.close()
		except Error as e:
			print(e)

	def highlighted(self, state):
		if state:
			return "color: rgb(245, 121, 0);"
		else:
			return ""

	def readpreferences(self):
		try:
			conn = sqlite3.connect(self.database)
			c = conn.cursor()
			c.execute("select * from preferences where id = 1")
			pref = c.fetchall()
			if len(pref) > 0:
				for x in pref:
					_, self.mycall, self.myclass, self.mysection, self.power, _, _, _, _, self.qrzname, self.qrzpass, self.qrzurl, self.cloudlogapi, self.cloudlogurl, useqrz, usecloudlog, userigcontrol, self.rigctrlhost, self.rigctrlport, self.markerfile, self.usemarker, self.usehamdb = x
					self.mycallEntry.setText(self.mycall)
					if self.mycall != "": self.mycallEntry.setStyleSheet("border: 1px solid green;")
					self.myclassEntry.setText(self.myclass)
					if self.myclass != "": self.myclassEntry.setStyleSheet("border: 1px solid green;")
					self.mysectionEntry.setText(self.mysection)
					if self.mysection != "": self.mysectionEntry.setStyleSheet("border: 1px solid green;")
					self.power_selector.setValue(int(self.power))
					self.usecloudlog = bool(usecloudlog)
					self.useqrz = bool(useqrz)
					self.userigctl = bool(userigcontrol)
					self.usemarker = bool(self.usemarker)
					self.usehamdb = bool(self.usehamdb)
			else:
				sql = f"INSERT INTO preferences(id, mycallsign, myclass, mysection, power, altpower, outdoors, notathome, satellite, markerfile, usemarker, usehamdb) VALUES(1,'{self.mycall}','{self.myclass}','{self.mysection}','{self.power}',{0},{0},{0},{0},'{self.markerfile}',{int(self.usemarker)},{int(self.usehamdb)})"
				c.execute(sql)
				conn.commit()
			conn.close()
		except Error as e:
			print(e)

	def writepreferences(self):
		try:
			conn = sqlite3.connect(self.database)
			sql = f"UPDATE preferences SET mycallsign = '{self.mycall}', myclass = '{self.myclass}', mysection = '{self.mysection}', power = '{self.power_selector.value()}', markerfile = '{self.markerfile}', usemarker = {int(self.usemarker)}, usehamdb = {int(self.usehamdb)} WHERE id = 1"
			cur = conn.cursor()
			cur.execute(sql)
			conn.commit()
			conn.close()
		except Error as e:
			print("Error:",e)

	def log_contact(self):
		if(len(self.callsign_entry.text()) == 0 or len(self.class_entry.text()) == 0 or len(self.section_entry.text()) == 0): return
		grid, opname = self.qrzlookup(self.callsign_entry.text())
		if not self.userigctl:
			self.oldfreq = int(float(self.dfreq[self.band]) * 1000000)
		contact = (self.callsign_entry.text(), self.class_entry.text(), self.section_entry.text(), self.oldfreq, self.band, self.mode, int(self.power_selector.value()), grid, opname)

		""" Just playing with server backend
		loggerhost = "127.0.0.1"
		loggerport = 7288
		with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
			s.connect((loggerhost, loggerport))
			s.sendall(f'<CMD><SAVEQSO><VALUE>{self.callsign_entry.text()} {self.class_entry.text()} {self.section_entry.text()} {self.oldfreq} {self.band} {self.mode} {int(self.power_selector.value())} {grid} {opname.replace(" ","_")}</VALUE></CMD>'.encode())
			s.close()
		"""

		try:
			conn = sqlite3.connect(self.database)
			sql = "INSERT INTO contacts(callsign, class, section, date_time, frequency, band, mode, power, grid, opname) VALUES(?,?,?,datetime('now'),?,?,?,?,?,?)"
			cur = conn.cursor()
			cur.execute(sql, contact)
			conn.commit()
			conn.close()
		except Error as e:
			print("Log Contact: ")
			print(e)

		self.sections()
		self.stats()
		self.updatemarker()
		self.logwindow()
		self.clearinputs()
		self.postcloudlog()

	def stats(self):
		conn = sqlite3.connect(self.database)
		c = conn.cursor()
		c.execute("select count(*) from contacts where mode = 'CW'")
		self.Total_CW.setText(str(c.fetchone()[0]))
		c.execute("select count(*) from contacts where mode = 'PH'")
		self.Total_Phone.setText(str(c.fetchone()[0]))
		c.execute("select count(*) from contacts where mode = 'DI'")
		self.Total_Digital.setText(str(c.fetchone()[0]))
		c.execute("select distinct band, mode from contacts")
		self.bandmodemult = len(c.fetchall())
		c.execute("SELECT count(*) FROM contacts where datetime(date_time) >=datetime('now', '-15 Minutes')")
		self.QSO_Last15.setText(str(c.fetchone()[0]))
		c.execute("SELECT count(*) FROM contacts where datetime(date_time) >=datetime('now', '-1 Hours')")
		self.QSO_PerHour.setText(str(c.fetchone()[0]))
		conn.close()
		self.QSO_Points.setText(str(self.calcscore()))

	def calcscore(self):
		self.qrpcheck()
		conn = sqlite3.connect(self.database)
		c = conn.cursor()
		c.execute("select count(*) as cw from contacts where mode = 'CW'")
		cw = str(c.fetchone()[0])
		c.execute("select count(*) as ph from contacts where mode = 'PH'")
		ph = str(c.fetchone()[0])
		c.execute("select count(*) as di from contacts where mode = 'DI'")
		di = str(c.fetchone()[0])
		c.execute("select distinct band, mode from contacts")
		self.bandmodemult = len(c.fetchall())
		conn.close()
		self.score = (int(cw) * 2) + int(ph) + (int(di) * 2)
		self.basescore = self.score
		self.powermult = 1
		if self.qrp:
			self.powermult = 5
			self.score = self.score * 5
		elif not (self.highpower):
			self.powermult = 2
			self.score = self.score * 2
		return self.score

	def qrpcheck(self):
		"""qrp = 5W cw, 10W ph and di, highpower greater than 150W"""
		conn = sqlite3.connect(self.database)
		c = conn.cursor()
		c.execute("select count(*) as qrpc from contacts where mode = 'CW' and power > 5")
		log = c.fetchall()
		qrpc = list(log[0])[0]
		c.execute("select count(*) as qrpp from contacts where mode = 'PH' and power > 10")
		log = c.fetchall()
		qrpp = list(log[0])[0]
		c.execute("select count(*) as qrpd from contacts where mode = 'DI' and power > 10")
		log = c.fetchall()
		qrpd = list(log[0])[0]
		c.execute("select count(*) as highpower from contacts where power > 150")
		log = c.fetchall()
		self.highpower = bool(list(log[0])[0])
		conn.close()
		self.qrp = not (qrpc + qrpp + qrpd)

	def logwindow(self):
		self.listWidget.clear()
		conn = sqlite3.connect(self.database)
		c = conn.cursor()
		c.execute("select * from contacts order by date_time desc")
		log = c.fetchall()
		conn.close()
		for x in log:
			logid, hiscall, hisclass, hissection, datetime, frequency,band, mode, power, _, _ = x
			logline = f"{str(logid).rjust(3,'0')} {hiscall.ljust(15)} {hisclass.rjust(3)} {hissection.rjust(3)} {datetime} {str(frequency).rjust(9)} {str(band).rjust(3)}M {mode} {str(power).rjust(3)}W"
			self.listWidget.addItem(logline)
	
	def qsoclicked(self):
		item = self.listWidget.currentItem()
		self.linetopass = item.text()
		dialog = editQSODialog(self)
		dialog.exec()

	def readSections(self):
		try:
			fd = open(self.relpath("arrl_sect.dat"), "r")  # read section data
			while 1:
				ln = fd.readline().strip()  # read a line and put in db
				if not ln: break
				if ln[0] == '#': continue
				try:
					_, st, canum, abbrev, name = str.split(ln, None, 4)
					self.secName[abbrev] = abbrev + ' ' + name + ' ' + canum
					self.secState[abbrev] = st
					for i in range(len(abbrev) - 1):
						p = abbrev[:-i - 1]
						self.secPartial[p] = 1
				except ValueError as e:
					print("rd arrl sec dat err, itm skpd: ", e)
			fd.close()
		except IOError as e:
			print("read error during readSections", e)
	
	def sectionCheck(self):
		self.infobox.clear()
		self.infobox.setTextColor(QtGui.QColor(211, 215, 207))
		sec = self.section_entry.text()
		if sec == "": sec = "^"
		x = list(self.secName.keys())
		xx = list(filter(lambda y: y.startswith(sec), x))
		for xxx in xx:
			self.infobox.insertPlainText(self.secName[xxx]+"\n")

	def readSCP(self):
		f = open(self.relpath("MASTER.SCP"))
		self.scp = f.readlines()
		f.close()
		self.scp = list(map(lambda x: x.strip(), self.scp))

	def superCheck(self):
		self.infobox.clear()
		self.infobox.setTextColor(QtGui.QColor(211, 215, 207))
		acall = self.callsign_entry.text()
		if(len(acall)>2):
			matches = list(filter(lambda x: x.startswith(acall), self.scp))
			for x in matches:
				self.infobox.insertPlainText(x+" ")
				pass

	def dupCheck(self):
		acall = self.callsign_entry.text()
		self.infobox.clear()
		conn = sqlite3.connect(self.database)
		c = conn.cursor()
		c.execute(f"select callsign, class, section, band, mode from contacts where callsign like '{acall}' order by band")
		log = c.fetchall()
		conn.close()
		for x in log:
			hiscall, hisclass, hissection, hisband, hismode = x
			if len(self.class_entry.text()) == 0: self.class_entry.setText(hisclass)
			if len(self.section_entry.text()) == 0: self.section_entry.setText(hissection)
			dupetext=""
			if hisband == self.band and hismode == self.mode:
				self.flash()
				self.infobox.setTextColor(QtGui.QColor(245, 121, 0))
				dupetext = " DUP!!!"
			else:
				self.infobox.setTextColor(QtGui.QColor(211, 215, 207))
			self.infobox.insertPlainText(f"{hiscall}: {hisband} {hismode}{dupetext}\n")

	def workedSections(self):
		conn = sqlite3.connect(self.database)
		c = conn.cursor()
		c.execute("select distinct section from contacts")
		all_rows = c.fetchall()
		self.wrkdsections = str(all_rows)
		self.wrkdsections = self.wrkdsections.replace("('", "").replace("',), ", ",").replace("',)]", "").replace('[', '').split(',')

	def workedSection(self, section):
		if section in self.wrkdsections:
			return "color: rgb(245, 121, 0);"
		else:
			return "color: rgb(136, 138, 133);"

	def sectionsCol1(self):
		self.Section_DX.setStyleSheet(self.workedSection("DX"))
		self.Section_CT.setStyleSheet(self.workedSection("CT"))
		self.Section_RI.setStyleSheet(self.workedSection("RI"))
		self.Section_EMA.setStyleSheet(self.workedSection("EMA"))
		self.Section_VT.setStyleSheet(self.workedSection("VT"))
		self.Section_ME.setStyleSheet(self.workedSection("ME"))
		self.Section_WMA.setStyleSheet(self.workedSection("WMA"))
		self.Section_NH.setStyleSheet(self.workedSection("NH"))
		self.Section_ENY.setStyleSheet(self.workedSection("ENY"))
		self.Section_NNY.setStyleSheet(self.workedSection("NNY"))
		self.Section_NLI.setStyleSheet(self.workedSection("NLI"))
		self.Section_SNJ.setStyleSheet(self.workedSection("SNJ"))
		self.Section_NNJ.setStyleSheet(self.workedSection("NNJ"))
		self.Section_WNY.setStyleSheet(self.workedSection("WNY"))

	def sectionsCol2(self):
		self.Section_DE.setStyleSheet(self.workedSection("DE"))
		self.Section_MDC.setStyleSheet(self.workedSection("MDC"))
		self.Section_EPA.setStyleSheet(self.workedSection("EPA"))
		self.Section_WPA.setStyleSheet(self.workedSection("WPA"))
		self.Section_AL.setStyleSheet(self.workedSection("AL"))
		self.Section_SC.setStyleSheet(self.workedSection("SC"))
		self.Section_GA.setStyleSheet(self.workedSection("GA"))
		self.Section_SFL.setStyleSheet(self.workedSection("SFL"))
		self.Section_KY.setStyleSheet(self.workedSection("KY"))
		self.Section_TN.setStyleSheet(self.workedSection("TN"))
		self.Section_NC.setStyleSheet(self.workedSection("NC"))
		self.Section_VA.setStyleSheet(self.workedSection("VA"))
		self.Section_NFL.setStyleSheet(self.workedSection("NFL"))
		self.Section_VI.setStyleSheet(self.workedSection("VI"))
		self.Section_PR.setStyleSheet(self.workedSection("PR"))
		self.Section_WCF.setStyleSheet(self.workedSection("WCF"))

	def sectionsCol3(self):
		self.Section_AR.setStyleSheet(self.workedSection("AR"))
		self.Section_NTX.setStyleSheet(self.workedSection("NTX"))
		self.Section_LA.setStyleSheet(self.workedSection("LA"))
		self.Section_OK.setStyleSheet(self.workedSection("OK"))
		self.Section_MS.setStyleSheet(self.workedSection("MS"))
		self.Section_STX.setStyleSheet(self.workedSection("STX"))
		self.Section_NM.setStyleSheet(self.workedSection("NM"))
		self.Section_WTX.setStyleSheet(self.workedSection("WTX"))
		self.Section_EB.setStyleSheet(self.workedSection("EB"))
		self.Section_SCV.setStyleSheet(self.workedSection("SCV"))
		self.Section_LAX.setStyleSheet(self.workedSection("LAX"))
		self.Section_SDG.setStyleSheet(self.workedSection("SDG"))
		self.Section_ORG.setStyleSheet(self.workedSection("ORG"))
		self.Section_SF.setStyleSheet(self.workedSection("SF"))
		self.Section_PAC.setStyleSheet(self.workedSection("PAC"))
		self.Section_SJV.setStyleSheet(self.workedSection("SJV"))
		self.Section_SB.setStyleSheet(self.workedSection("SB"))
		self.Section_SV.setStyleSheet(self.workedSection("SV"))

	def sectionsCol4(self):
		self.Section_AK.setStyleSheet(self.workedSection("AK"))
		self.Section_NV.setStyleSheet(self.workedSection("NV"))
		self.Section_AZ.setStyleSheet(self.workedSection("AZ"))
		self.Section_OR.setStyleSheet(self.workedSection("OR"))
		self.Section_EWA.setStyleSheet(self.workedSection("EWA"))
		self.Section_UT.setStyleSheet(self.workedSection("UT"))
		self.Section_ID.setStyleSheet(self.workedSection("ID"))
		self.Section_WWA.setStyleSheet(self.workedSection("WWA"))
		self.Section_MT.setStyleSheet(self.workedSection("MT"))
		self.Section_WY.setStyleSheet(self.workedSection("WY"))
		self.Section_MI.setStyleSheet(self.workedSection("MI"))
		self.Section_WV.setStyleSheet(self.workedSection("WV"))
		self.Section_OH.setStyleSheet(self.workedSection("OH"))
		self.Section_IL.setStyleSheet(self.workedSection("IL"))
		self.Section_WI.setStyleSheet(self.workedSection("WI"))
		self.Section_IN.setStyleSheet(self.workedSection("IN"))

	def sectionsCol5(self):
		self.Section_CO.setStyleSheet(self.workedSection("CO"))
		self.Section_MO.setStyleSheet(self.workedSection("MO"))
		self.Section_IA.setStyleSheet(self.workedSection("IA"))
		self.Section_ND.setStyleSheet(self.workedSection("ND"))
		self.Section_KS.setStyleSheet(self.workedSection("KS"))
		self.Section_NE.setStyleSheet(self.workedSection("NE"))
		self.Section_MN.setStyleSheet(self.workedSection("MN"))
		self.Section_SD.setStyleSheet(self.workedSection("SD"))
		self.Section_AB.setStyleSheet(self.workedSection("AB"))
		self.Section_NT.setStyleSheet(self.workedSection("NT"))
		self.Section_BC.setStyleSheet(self.workedSection("BC"))
		self.Section_ONE.setStyleSheet(self.workedSection("ONE"))
		self.Section_GTA.setStyleSheet(self.workedSection("GTA"))
		self.Section_ONN.setStyleSheet(self.workedSection("ONN"))
		self.Section_MAR.setStyleSheet(self.workedSection("MAR"))
		self.Section_ONS.setStyleSheet(self.workedSection("ONS"))
		self.Section_MB.setStyleSheet(self.workedSection("MB"))
		self.Section_QC.setStyleSheet(self.workedSection("QC"))
		self.Section_NL.setStyleSheet(self.workedSection("NL"))
		self.Section_SK.setStyleSheet(self.workedSection("SK"))
		self.Section_PE.setStyleSheet(self.workedSection("PE"))

	def sections(self):
		self.workedSections()
		self.sectionsCol1()
		self.sectionsCol2()
		self.sectionsCol3()
		self.sectionsCol4()
		self.sectionsCol5()

	def getBandModeTally(self, band, mode):
		conn = ""
		conn = sqlite3.connect(self.database)
		c = conn.cursor()
		c.execute(f"select count(*) as tally, MAX(power) as mpow from contacts where band = '{band}' AND mode ='{mode}'")
		return c.fetchone()

	def getbands(self):
		bandlist=[]
		conn = sqlite3.connect(self.database)
		c = conn.cursor()
		c.execute("select DISTINCT band from contacts")
		x=c.fetchall()
		if x:
			for count in x:
				bandlist.append(count[0])
			return bandlist
		return []

	def generateBandModeTally(self):
		blist = self.getbands()
		bmtfn = "Statistics.txt"
		print("\t\tCW\tPWR\tDI\tPWR\tPH\tPWR", end='\r\n', file=open(bmtfn, "w"))
		print("-"*60, end='\r\n', file=open(bmtfn, "a"))
		for b in self.bands:
			if b in blist:
				cwt = self.getBandModeTally(b,"CW")
				dit = self.getBandModeTally(b,"DI")
				pht = self.getBandModeTally(b,"PH")
				print(f"Band:\t{b}\t{cwt[0]}\t{cwt[1]}\t{dit[0]}\t{dit[1]}\t{pht[0]}\t{pht[1]}", end='\r\n', file=open(bmtfn, "a"))
				print("-"*60, end='\r\n', file=open(bmtfn, "a"))

	def getState(self, section):
		try:
			state = self.secState[section]
			if state != "--":
				return state
		except:
			return False
		return False

	def gridtolatlon(self, maiden):
		maiden = str(maiden).strip().upper()

		N = len(maiden)
		if not 8 >= N >= 2 and N % 2 == 0:
			return 0,0

		lon = (ord(maiden[0]) - 65) * 20 - 180
		lat = (ord(maiden[1]) - 65) * 10 - 90

		if N >= 4:
			lon += (ord(maiden[2])-48) * 2
			lat += (ord(maiden[3])-48)

		if N >= 6:
			lon += (ord(maiden[4]) - 65) / 12 + 1 / 24
			lat += (ord(maiden[5]) - 65) / 24 + 1 / 48

		if N >= 8:
			lon += (ord(maiden[6])) * 5.0 / 600
			lat += (ord(maiden[7])) * 2.5 / 600

		return lat, lon

	def updatemarker(self):
		if self.usemarker:
			filename = str(Path.home())+"/"+self.markerfile
			print("", file=open(filename, "w", encoding='ascii'))
			conn = sqlite3.connect(self.database)
			c = conn.cursor()
			c.execute("select DISTINCT grid from contacts")
			x=c.fetchall()
			if x:
				for count in x:
					grid = count[0]
					if len(grid) > 1:
						lat, lon = self.gridtolatlon(grid)
						print(f'{lat} {lon} ""', end='\r\n', file=open(filename, "a", encoding='ascii'))

	def qrzlookup(self, call):
		grid = False
		name = False
		internet_good = self.has_internet()
		try:
			if self.qrzsession and self.useqrz and internet_good:
				payload = {'s':self.qrzsession, 'callsign':call}
				r=requests.get(self.qrzurl,params=payload, timeout=3.0)
				if not r.text.find('<Key>'): #key expired get a new one
					self.qrzauth()
					if self.qrzsession:
						payload = {'s':self.qrzsession, 'callsign':call}
						r=requests.get(self.qrzurl,params=payload, timeout=3.0)
				grid, name = self.parseLookup(r)
			elif self.usehamdb and internet_good:
				r=requests.get(f"http://api.hamdb.org/v1/{call}/xml/k6gtefdlogger",timeout=3.0)
				grid, name = self.parseLookup(r)
		except:
			self.infobox.insertPlainText(f"Something Smells...\n")
		return grid, name

	def parseLookup(self,r):
		grid=False
		name=False
		try:
			if r.status_code == 200:
				if r.text.find('<Error>') > 0:
					errorText = r.text[r.text.find('<Error>')+7:r.text.find('</Error>')]
					self.infobox.insertPlainText(f"\nQRZ/HamDB Error: {errorText}\n")
				if r.text.find('<grid>') > 0:
					grid = r.text[r.text.find('<grid>')+6:r.text.find('</grid>')]
				if r.text.find('<fname>') > 0:
					name = r.text[r.text.find('<fname>')+7:r.text.find('</fname>')]
				if r.text.find('<name>') > 0:
					if not name:
						name = r.text[r.text.find('<name>')+6:r.text.find('</name>')]
					else:
						name += " " + r.text[r.text.find('<name>')+6:r.text.find('</name>')]
		except:
			self.infobox.insertPlainText(f"Lookup Failed...\n")
		return grid, name

	def adif(self):
		logname = "FieldDay.adi"
		self.infobox.setTextColor(QtGui.QColor(211, 215, 207))
		self.infobox.insertPlainText("Saving ADIF to: "+logname+"\n")
		app.processEvents()
		conn = sqlite3.connect(self.database)
		c = conn.cursor()
		c.execute("select * from contacts order by date_time ASC")
		log = c.fetchall()
		conn.close()
		grid = False
		opname = False
		print("<ADIF_VER:5>2.2.0", end='\r\n', file=open(logname, "w", encoding='ascii'))
		print("<EOH>", end='\r\n', file=open(logname, "a", encoding='ascii'))
		for x in log:
			_, hiscall, hisclass, hissection, datetime, freq, band, mode, _, grid, opname = x
			if mode == "DI": mode = "FT8"
			if mode == "PH": mode = "SSB"
			if mode == "CW":
				rst = "599"
			else:
				rst = "59"
			loggeddate = datetime[:10]
			loggedtime = datetime[11:13] + datetime[14:16]

			temp = str(freq/1000000).split('.')
			freq = temp[0] + "." + temp[1].ljust(3,'0')

			print(f"<QSO_DATE:{len(''.join(loggeddate.split('-')))}:d>{''.join(loggeddate.split('-'))}", end='\r\n', file=open(logname, 'a', encoding='ascii'))
			print(f"<TIME_ON:{len(loggedtime)}>{loggedtime}", end='\r\n', file=open(logname, 'a', encoding='ascii'))
			print(f"<CALL:{len(hiscall)}>{hiscall}", end='\r\n', file=open(logname, 'a', encoding='ascii'))
			print(f"<MODE:{len(mode)}>{mode}", end='\r\n', file=open(logname, 'a', encoding='ascii'))
			print(f"<BAND:{len(band + 'M')}>{band + 'M'}", end='\r\n', file=open(logname, 'a', encoding='ascii'))
			print(f"<FREQ:{len(freq)}>{freq}", end='\r\n', file=open(logname, 'a', encoding='ascii'))
			print(f"<RST_SENT:{len(rst)}>{rst}", end='\r\n', file=open(logname, 'a', encoding='ascii'))
			print(f"<RST_RCVD:{len(rst)}>{rst}", end='\r\n', file=open(logname, 'a', encoding='ascii'))
			print(f"<STX_STRING:{len(self.myclass + ' ' + self.mysection)}>{self.myclass + ' ' + self.mysection}", end='\r\n', file=open(logname, 'a', encoding='ascii'))
			print(f"<SRX_STRING:{len(hisclass + ' ' + hissection)}>{hisclass + ' ' + hissection}", end='\r\n', file=open(logname, 'a', encoding='ascii'))
			print(f"<ARRL_SECT:{len(hissection)}>{hissection}", end='\r\n', file=open(logname, 'a', encoding='ascii'))
			print(f"<CLASS:{len(hisclass)}>{hisclass}", end='\r\n', file=open(logname, 'a', encoding='ascii'))
			state = self.getState(hissection)
			if state: print(f"<STATE:{len(state)}>{state}", end='\r\n', file=open(logname, 'a', encoding='ascii'))
			if len(grid) > 1: print(f"<GRIDSQUARE:{len(grid)}>{grid}", end='\r\n', file=open(logname, 'a', encoding='ascii'))
			if len(opname) > 1: print(f"<NAME:{len(opname)}>{opname}", end='\r\n', file=open(logname, 'a', encoding='ascii'))
			comment = "ARRL-FD"
			print(f"<COMMENT:{len(comment)}>{comment}", end='\r\n', file=open(logname, 'a', encoding='ascii'))
			print("<EOR>", end='\r\n', file=open(logname, 'a', encoding='ascii'))
			print("", end='\r\n', file=open(logname, 'a', encoding='ascii'))
		self.infobox.insertPlainText("Done\n\n")
		app.processEvents()

	def postcloudlog(self):
		if (not self.usecloudlog) or (not self.cloudlogauthenticated): return
		conn = sqlite3.connect(self.database)
		c = conn.cursor()
		c.execute("select * from contacts order by id DESC")
		q = c.fetchone()
		conn.close()
		_, hiscall, hisclass, hissection, datetime, band, mode, _, grid, opname = q
			
		if mode == "DI": mode = "FT8"
		if mode == "PH": mode = "SSB"
		if mode == "CW":
			rst = "599"
		else:
			rst = "59"
		loggeddate = datetime[:10]
		loggedtime = datetime[11:13] + datetime[14:16]
		adifq = f"<QSO_DATE:{len(''.join(loggeddate.split('-')))}:d>{''.join(loggeddate.split('-'))}"
		adifq += f"<TIME_ON:{len(loggedtime)}>{loggedtime}"
		adifq += f"<CALL:{len(hiscall)}>{hiscall}"
		adifq += f"<MODE:{len(mode)}>{mode}"
		adifq += f"<BAND:{len(band + 'M')}>{band + 'M'}"
		adifq += f"<FREQ:{len(self.dfreq[band])}>{self.dfreq[band]}"
		adifq += f"<RST_SENT:{len(rst)}>{rst}"
		adifq += f"<RST_RCVD:{len(rst)}>{rst}"
		adifq += f"<STX_STRING:{len(self.myclass + ' ' + self.mysection)}>{self.myclass + ' ' + self.mysection}"
		adifq += f"<SRX_STRING:{len(hisclass + ' ' + hissection)}>{hisclass + ' ' + hissection}"
		adifq += f"<ARRL_SECT:{len(hissection)}>{hissection}"
		adifq += f"<CLASS:{len(hisclass)}>{hisclass}"
		state = self.getState(hissection)
		if state: adifq += f"<STATE:{len(state)}>{state}"
		if len(grid) > 1: adifq += f"<GRIDSQUARE:{len(grid)}>{grid}"
		if len(opname) > 1: adifq += f"<NAME:{len(opname)}>{opname}"
		comment = "ARRL-FD"
		adifq += f"<COMMENT:{len(comment)}>{comment}"
		adifq += "<EOR>"

		payloadDict = {
			"key":self.cloudlogapi,
			"type":"adif",
			"string":adifq
		}
		jsonData = json.dumps(payloadDict)
		_ = requests.post(self.cloudlogurl, jsonData)

	def cabrillo(self):
		filename = self.mycall.upper()+".log"
		self.infobox.setTextColor(QtGui.QColor(211, 215, 207))
		self.infobox.insertPlainText(f"Saving cabrillo to: {filename}")
		app.processEvents()
		conn = sqlite3.connect(self.database)
		c = conn.cursor()
		c.execute("select * from contacts order by date_time ASC")
		log = c.fetchall()
		conn.close()
		catpower = ""
		if self.qrp:
			catpower = "QRP"
		elif self.highpower:
			catpower = "HIGH"
		else:
			catpower = "LOW"
		
		print("START-OF-LOG: 3.0", end='\r\n', file=open(filename, "w", encoding='ascii'))
		print("CREATED-BY: K6GTE Field Day Logger", end='\r\n', file=open(filename, "a", encoding='ascii'))
		print("CONTEST: ARRL-FD", end='\r\n', file=open(filename, "a", encoding='ascii'))
		print(f"CALLSIGN: {self.mycall}", end='\r\n', file=open(filename, "a", encoding='ascii'))
		print("LOCATION:", end='\r\n', file=open(filename, "a", encoding='ascii'))
		print(f"ARRL-SECTION: {self.mysection}", end='\r\n', file=open(filename, "a", encoding='ascii'))
		print(f"CATEGORY: {self.myclass}", end='\r\n', file=open(filename, "a", encoding='ascii'))
		print(f"CATEGORY-POWER: {catpower}", end='\r\n', file=open(filename, "a", encoding='ascii'))
		print(f"CLAIMED-SCORE: {self.calcscore()}", end='\r\n', file=open(filename, "a", encoding='ascii'))
		print(f"OPERATORS: {self.mycall}", end='\r\n', file=open(filename, "a", encoding='ascii'))
		print("NAME: ", end='\r\n', file=open(filename, "a", encoding='ascii'))
		print("ADDRESS: ", end='\r\n', file=open(filename, "a", encoding='ascii'))
		print("ADDRESS-CITY: ", end='\r\n', file=open(filename, "a", encoding='ascii'))
		print("ADDRESS-STATE: ", end='\r\n', file=open(filename, "a", encoding='ascii'))
		print("ADDRESS-POSTALCODE: ", end='\r\n', file=open(filename, "a", encoding='ascii'))
		print("ADDRESS-COUNTRY: ", end='\r\n', file=open(filename, "a", encoding='ascii'))
		print("EMAIL: ", end='\r\n', file=open(filename, "a", encoding='ascii'))
		for x in log:
			_, hiscall, hisclass, hissection, datetime, freq, _, mode, _, _, _ = x
			if mode == "DI": mode = "DG"
			loggeddate = datetime[:10]
			loggedtime = datetime[11:13] + datetime[14:16]

			temp = str(freq/1000000).split('.')
			freq = temp[0] + temp[1].ljust(3,'0')[:3]

			print(f"QSO: {freq.rjust(6)} {mode} {loggeddate} {loggedtime} {self.mycall} {self.myclass} {self.mysection} {hiscall} {hisclass} {hissection}", end='\r\n', file=open(filename, "a", encoding='ascii'))
		print("END-OF-LOG:", end='\r\n', file=open(filename, "a", encoding='ascii'))
		self.infobox.insertPlainText(" Done\n\n")
		app.processEvents()

	def generateLogs(self):
		self.infobox.clear()
		self.cabrillo()
		self.generateBandModeTally()
		self.adif()

class editQSODialog(QtWidgets.QDialog):

	theitem=""

	def __init__(self, parent=None):
		super().__init__(parent)
		uic.loadUi(self.relpath("dialog.ui"), self)
		self.theitem, thecall, theclass, thesection, thedate, thetime, thefreq, theband, themode, thepower = window.linetopass.split()
		self.editCallsign.setText(thecall)
		self.editClass.setText(theclass)
		self.editSection.setText(thesection)
		self.editFreq.setText(thefreq)
		self.editBand.setCurrentIndex(self.editBand.findText(theband.replace("M","")))
		self.editMode.setCurrentIndex(self.editMode.findText(themode))
		self.editPower.setValue(int(thepower[:len(thepower)-1]))
		date_time = thedate+" "+thetime
		now = QtCore.QDateTime.fromString(date_time, 'yyyy-MM-dd hh:mm:ss')
		self.editDateTime.setDateTime(now)
		self.deleteButton.clicked.connect(self.delete_contact)
		self.buttonBox.accepted.connect(self.saveChanges)

	def relpath(self, filename):
		try:
			base_path = sys._MEIPASS # pylint: disable=no-member
		except:
			base_path = os.path.abspath(".")
		return os.path.join(base_path, filename)

	def saveChanges(self):
		try:
			conn = sqlite3.connect(window.database)
			sql = f"update contacts set callsign = '{self.editCallsign.text()}', class = '{self.editClass.text()}', section = '{self.editSection.text()}', date_time = '{self.editDateTime.text()}', frequency = '{self.editFreq.text()}', band = '{self.editBand.currentText()}', mode = '{self.editMode.currentText()}', power = '{self.editPower.value()}'  where id={self.theitem}"
			cur = conn.cursor()
			cur.execute(sql)
			conn.commit()
			conn.close()
		except Error as e:
			print(e)
		window.sections()
		window.stats()
		window.logwindow()

	def delete_contact(self):
		try:
			conn = sqlite3.connect(window.database)
			sql = f"delete from contacts where id={self.theitem}"
			cur = conn.cursor()
			cur.execute(sql)
			conn.commit()
			conn.close()
		except Error as e:
			print(e)
		window.sections()
		window.stats()
		window.logwindow()
		self.close()

class settings(QtWidgets.QDialog):
	def __init__(self, parent=None):
		super().__init__(parent)
		uic.loadUi(self.relpath("settings.ui"), self)
		self.buttonBox.accepted.connect(self.saveChanges)
		try:
			conn = sqlite3.connect(window.database)
			c = conn.cursor()	
			c.execute("select * from preferences where id = 1")
			pref = c.fetchall()
			if len(pref) > 0:
				for x in pref:
					_, _, _, _, _, _, _, _, _, qrzname, qrzpass, qrzurl, cloudlogapi, cloudlogurl, useqrz, usecloudlog, userigcontrol, rigctrlhost, rigctrlport, markerfile, usemarker, usehamdb = x
					self.qrzname_field.setText(qrzname)
					self.qrzpass_field.setText(qrzpass)
					self.qrzurl_field.setText(qrzurl)
					self.cloudlogapi_field.setText(cloudlogapi)
					self.cloudlogurl_field.setText(cloudlogurl)
					self.rigcontrolip_field.setText(rigctrlhost)
					self.rigcontrolport_field.setText(rigctrlport)
					self.usecloudlog_checkBox.setChecked(bool(usecloudlog))
					self.useqrz_checkBox.setChecked(bool(useqrz))
					self.userigcontrol_checkBox.setChecked(bool(userigcontrol))
					self.markerfile_field.setText(markerfile)
					self.generatemarker_checkbox.setChecked(bool(usemarker))
					self.usehamdb_checkBox.setChecked(bool(usehamdb))

		except Error as e:
			print(e)

	def relpath(self, filename):
		try:
			base_path = sys._MEIPASS # pylint: disable=no-member
		except:
			base_path = os.path.abspath(".")
		return os.path.join(base_path, filename)

	def saveChanges(self):
		try:
			conn = sqlite3.connect(window.database)
			sql = f"UPDATE preferences SET qrzusername = '{self.qrzname_field.text()}', qrzpassword = '{self.qrzpass_field.text()}', qrzurl = '{self.qrzurl_field.text()}', cloudlogapi = '{self.cloudlogapi_field.text()}', cloudlogurl = '{self.cloudlogurl_field.text()}', rigcontrolip = '{self.rigcontrolip_field.text()}', rigcontrolport = '{self.rigcontrolport_field.text()}', useqrz = '{int(self.useqrz_checkBox.isChecked())}', usecloudlog = '{int(self.usecloudlog_checkBox.isChecked())}', userigcontrol = '{int(self.userigcontrol_checkBox.isChecked())}', markerfile = '{self.markerfile_field.text()}', usemarker = '{int(self.generatemarker_checkbox.isChecked())}', usehamdb = '{int(self.usehamdb_checkBox.isChecked())}'  where id=1;"
			cur = conn.cursor()
			cur.execute(sql)
			conn.commit()
			conn.close()
		except Error as e:
			print(e)


app = QtWidgets.QApplication(sys.argv)
app.setStyle('Fusion')
window = MainWindow()
window.show()
window.create_DB()
window.changeband()
window.changemode()
window.readpreferences()
window.qrzauth()
window.cloudlogauth()
window.stats()
window.readSections()
window.readSCP()
window.logwindow()
window.sections()
window.callsign_entry.setFocus()

def updatetime():
	now = datetime.now().isoformat(' ')[5:19].replace('-', '/')
	utcnow = datetime.utcnow().isoformat(' ')[5:19].replace('-', '/')
	window.localtime.setText(now)
	window.utctime.setText(utcnow)


timer = QtCore.QTimer()
timer.timeout.connect(updatetime)
timer.start(1000)


app.exec()
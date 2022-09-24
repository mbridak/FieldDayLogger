"""Database class to store contacts"""
import logging
import sqlite3


class DataBase:
    """Database class for our database."""

    def __init__(self, database):
        """initializes DataBase instance"""
        self.database = database
        self.create_db()

    def create_db(self) -> None:
        """
        create database tables contacts if they do not exist.
        """
        try:
            with sqlite3.connect(self.database) as conn:
                cursor = conn.cursor()
                sql_table = (
                    "CREATE TABLE IF NOT EXISTS contacts "
                    "(id INTEGER PRIMARY KEY, "
                    "unique_id text NOT NULL, "
                    "callsign text NOT NULL, "
                    "class text NOT NULL, "
                    "section text NOT NULL, "
                    "date_time text NOT NULL, "
                    "frequency INTEGER DEFAULT 0, "
                    "band text NOT NULL, "
                    "mode text NOT NULL, "
                    "power INTEGER NOT NULL, "
                    "grid text NOT NULL, "
                    "opname text NOT NULL, "
                    "station text NOT NULL);"
                )
                cursor.execute(sql_table)
                conn.commit()
        except sqlite3.Error as exception:
            logging.critical("create_db: Unable to create database: %s", exception)

    def log_contact(self, logme: tuple) -> None:
        """
        Inserts a contact into the db.
        pass in (unique_id, hiscall, hisclass, hissection, band, mode, int(power), grid, name)
        """
        try:
            with sqlite3.connect(self.database) as conn:
                sql = f"select count(*) from contacts where unique_id ='{logme[0]}';"
                cur = conn.cursor()
                cur.execute(sql)
                if cur.fetchone()[0] == 0:
                    sql = (
                        "INSERT INTO contacts"
                        "(unique_id, callsign, class, section, date_time, frequency, "
                        "band, mode, power, grid, opname, station) "
                        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)"
                    )
                    cur.execute(sql, logme)
                else:
                    sql = (
                        f"update contacts set callsign = '{logme[1]}', class = '{logme[2]}', "
                        f"section = '{logme[3]}', date_time = '{logme[4]}', band = '{logme[6]}', "
                        f"mode = '{logme[7]}', power = '{logme[8]}', station = '{logme[11]}', "
                        f"frequency = '{logme[5]}' where unique_id='{logme[0]}';"
                    )
                    cur.execute(sql)
                conn.commit()
        except sqlite3.Error as exception:
            logging.debug("DataBase log_contact: %s", exception)

    def delete_contact(self, unique_id) -> None:
        """Deletes a contact from the db by passing in UUID."""
        if unique_id:
            try:
                with sqlite3.connect(self.database) as conn:
                    sql = f"delete from contacts where unique_id='{unique_id}'"
                    cur = conn.cursor()
                    cur.execute(sql)
                    conn.commit()
            except sqlite3.Error as exception:
                logging.debug("DataBase delete_contact: %s", exception)

    def change_contact(self, qso):
        """Update an existing contact."""
        try:
            with sqlite3.connect(self.database) as conn:
                sql = (
                    f"update contacts set callsign = '{qso[0]}', class = '{qso[1]}', "
                    f"section = '{qso[2]}', date_time = '{qso[3]}', band = '{qso[4]}', "
                    f"mode = '{qso[5]}', power = '{qso[6]}', station = '{qso[7]}', "
                    f"frequency = '{qso[8]}' where unique_id='{qso[9]}';"
                )
                cur = conn.cursor()
                cur.execute(sql)
                conn.commit()
        except sqlite3.Error as exception:
            logging.critical("DataBase change_contact: %s", exception)

    def get_operators(self) -> list:
        """Return a list of station calls used."""
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            cursor.execute("select distinct station from contacts;")
            ops = cursor.fetchall()
        return ops

    def stats(self) -> tuple:
        """
        returns a tuple with some stats:
        cwcontacts, phonecontacts, digitalcontacts, bandmodemult, last15, lasthour, hignpower, qrp
        """
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            cursor.execute("select count(*) from contacts where mode = 'CW'")
            cwcontacts = str(cursor.fetchone()[0])
            cursor.execute("select count(*) from contacts where mode = 'PH'")
            phonecontacts = str(cursor.fetchone()[0])
            cursor.execute("select count(*) from contacts where mode = 'DI'")
            digitalcontacts = str(cursor.fetchone()[0])
            cursor.execute("select distinct band, mode from contacts")
            bandmodemult = len(cursor.fetchall())
            cursor.execute(
                "SELECT count(*) FROM contacts "
                "where datetime(date_time) >=datetime('now', '-15 Minutes')"
            )
            last15 = str(cursor.fetchone()[0])
            cursor.execute(
                "SELECT count(*) FROM contacts "
                "where datetime(date_time) >=datetime('now', '-1 Hours')"
            )
            lasthour = str(cursor.fetchone()[0])
            cursor.execute(
                "select count(*) as qrpc from contacts where mode = 'CW' and power > 5"
            )
            log = cursor.fetchall()
            qrpc = list(log[0])[0]
            cursor.execute(
                "select count(*) as qrpp from contacts where mode = 'PH' and power > 10"
            )
            log = cursor.fetchall()
            qrpp = list(log[0])[0]
            cursor.execute(
                "select count(*) as qrpd from contacts where mode = 'DI' and power > 10"
            )
            log = cursor.fetchall()
            qrpd = list(log[0])[0]
            cursor.execute(
                "select count(*) as highpower from contacts where power > 100"
            )
            log = cursor.fetchall()
            highpower = bool(list(log[0])[0])
            qrp = not qrpc + qrpp + qrpd

            return (
                cwcontacts,
                phonecontacts,
                digitalcontacts,
                bandmodemult,
                last15,
                lasthour,
                highpower,
                qrp,
            )

    def contacts_under_101watts(self) -> tuple:
        """return contact tallies for contacts made below 101 watts."""
        try:
            with sqlite3.connect(self.database) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "select count(*) as cw from contacts where mode = 'CW' and power < 101"
                )
                c_dubs = str(cursor.fetchone()[0])
                cursor.execute(
                    "select count(*) as ph from contacts where mode = 'PH' and power < 101"
                )
                phone = str(cursor.fetchone()[0])
                cursor.execute(
                    "select count(*) as di from contacts where mode = 'DI' and power < 101"
                )
                digital = str(cursor.fetchone()[0])
        except sqlite3.Error as exception:
            logging.critical("DB-contacts_under_101watts: %s", exception)
            return 0, 0, 0
        return c_dubs, phone, digital

    def qrp_check(self) -> tuple:
        """check to see if all contacts were QRP"""
        try:
            with sqlite3.connect(self.database) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "select count(*) as qrpc from contacts where mode = 'CW' and power > 5"
                )
                log = cursor.fetchall()
                qrpc = list(log[0])[0]
                cursor.execute(
                    "select count(*) as qrpp from contacts where mode = 'PH' and power > 10"
                )
                log = cursor.fetchall()
                qrpp = list(log[0])[0]
                cursor.execute(
                    "select count(*) as qrpd from contacts where mode = 'DI' and power > 10"
                )
                log = cursor.fetchall()
                qrpd = list(log[0])[0]
                cursor.execute(
                    "select count(*) as highpower from contacts where power > 100"
                )
                log = cursor.fetchall()
                highpower = bool(list(log[0])[0])
                qrp = not qrpc + qrpp + qrpd
        except sqlite3.Error as exception:
            logging.critical("qrpcheck: %s", exception)
            return 0, 0
        return qrp, highpower

    def get_band_mode_tally(self, band, mode):
        """
        returns the amount of contacts and the maximum power used
        for a given band using a particular mode.
        """
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "select count(*) as tally, MAX(power) as mpow from contacts "
                f"where band = '{band}' AND mode ='{mode}'"
            )
            return cursor.fetchone()

    def get_bands(self) -> tuple:
        """returns a list of bands"""
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            cursor.execute("select DISTINCT band from contacts")
            return cursor.fetchall()

    def fetch_all_contacts_asc(self) -> tuple:
        """returns a tuple of all contacts in the database."""
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            cursor.execute("select * from contacts order by date_time ASC")
            return cursor.fetchall()

    def fetch_all_contacts_desc(self) -> tuple:
        """returns a tuple of all contacts in the database."""
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            cursor.execute("select * from contacts order by date_time desc")
            return cursor.fetchall()

    def fetch_last_contact(self) -> tuple:
        """returns a tuple of all contacts in the database."""
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            cursor.execute("select * from contacts order by id desc")
            return cursor.fetchone()

    def dup_check(self, acall: str) -> tuple:
        """returns a list of possible dups"""
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "select callsign, class, section, band, mode "
                f"from contacts where callsign like '{acall}' order by band"
            )
            return cursor.fetchall()

    def sections(self) -> tuple:
        """returns a list of sections worked."""
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            cursor.execute("select distinct section from contacts")
            return cursor.fetchall()

    def contact_by_id(self, record) -> tuple:
        """returns a contact matching an id"""
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            cursor.execute("select * from contacts where id=" + record)
            return cursor.fetchall()

    def get_grids(self) -> tuple:
        """returns a tuple of unique grids in the log."""
        with sqlite3.connect(self.database) as conn:
            cursor = conn.cursor()
            cursor.execute("select DISTINCT grid from contacts")
            return cursor.fetchall()

"""Database class to store contacts"""
import logging
import sqlite3


class DataBase:
    """Database class for our database."""

    def __init__(self, database):
        """initializes DataBase instance"""
        self.logger = logging.getLogger("__name__")
        self.database = database
        self.create_db()

    @staticmethod
    def row_factory(cursor, row):
        """
        cursor.description:
        (name, type_code, display_size,
        internal_size, precision, scale, null_ok)
        row: (value, value, ...)
        """
        return {
            col[0]: row[idx]
            for idx, col in enumerate(
                cursor.description,
            )
        }

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
                    "unique_id text NOT NULL, "
                    "dirty INTEGER DEFAULT 1);"
                )
                cursor.execute(sql_table)
                conn.commit()
        except sqlite3.Error as exception:
            self.logger.critical("%s", exception)

    def clear_dirty_flag(self, unique_id) -> None:
        """Clears the dirty flag."""
        if unique_id:
            try:
                with sqlite3.connect(self.database) as conn:
                    sql = f"update contacts set dirty=0 where unique_id='{unique_id}';"
                    cursor = conn.cursor()
                    cursor.execute(sql)
                    conn.commit()
            except sqlite3.Error as exception:
                self.logger.critical("%s", exception)

    def log_contact(self, logme: tuple) -> None:
        """
        Inserts a contact into the db.
        pass in (hiscall, hisclass, hissection, band, mode, int(power), grid, name)
        """
        try:
            with sqlite3.connect(self.database) as conn:
                sql = (
                    "INSERT INTO contacts"
                    "(callsign, class, section, date_time, frequency, "
                    "band, mode, power, grid, opname, unique_id, dirty) "
                    "VALUES(?,?,?,datetime('now'),?,?,?,?,?,?,?,1)"
                )
                cur = conn.cursor()
                cur.execute(sql, logme)
                conn.commit()
        except sqlite3.Error as exception:
            self.logger.debug("DataBase log_contact: %s", exception)

    def get_unique_id(self, contact) -> str:
        """get unique id"""
        unique_id = ""
        if contact:
            try:
                with sqlite3.connect(self.database) as conn:
                    sql = f"select unique_id from contacts where id={int(contact)}"
                    cursor = conn.cursor()
                    cursor.execute(sql)
                    unique_id = str(cursor.fetchone()[0])
            except sqlite3.Error as exception:
                self.logger.debug("%s", exception)
        return unique_id

    def delete_contact(self, contact) -> None:
        """Deletes a contact from the db."""
        if contact:
            try:
                with sqlite3.connect(self.database) as conn:
                    sql = f"delete from contacts where id={int(contact)}"
                    cur = conn.cursor()
                    cur.execute(sql)
                    conn.commit()
            except sqlite3.Error as exception:
                self.logger.critical("DataBase delete_contact: %s", exception)

    def change_contact(self, qso):
        """Update an existing contact."""
        try:
            with sqlite3.connect(self.database) as conn:
                sql = (
                    f"update contacts set callsign = '{qso[0]}', class = '{qso[1]}', "
                    f"section = '{qso[2]}', date_time = '{qso[3]}', band = '{qso[4]}', "
                    f"mode = '{qso[5]}', power = '{qso[6]}', frequency = '{qso[7]}' "
                    f"where id='{qso[8]}';"
                )
                cur = conn.cursor()
                cur.execute(sql)
                conn.commit()
        except sqlite3.Error as exception:
            self.logger.critical("DataBase change_contact: %s", exception)

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
            self.logger.critical("DB-contacts_under_101watts: %s", exception)
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
            self.logger.critical("qrpcheck: %s", exception)
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

    def fetch_all_dirty_contacts(self) -> list:
        """
        Return a list of dict, containing all contacts still flagged as dirty.\n
        Example:\n
        {\n
            'id': 2, 'callsign': 'N6QW', 'class': '1B', 'section': 'SB', \n
            'date_time': '2022-09-22 18:44:02', 'frequency': 1830000, 'band': '160', \n
            'mode': 'CW', 'power': 5, 'grid': 'DM04md', 'opname': 'PETER JULIANO', \n
            'unique_id': '6fe98693f3ac4250847a6e5ac9da650e', 'dirty': 1\n
        }\n
        """
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = self.row_factory
            cursor = conn.cursor()
            cursor.execute("select * from contacts where dirty=1 order by id")
            return cursor.fetchall()

    def count_all_dirty_contacts(self) -> dict:
        """
        Returns a dict containing the count of contacts still flagged as dirty.\n
        Example: {'alldirty': 3}
        """
        with sqlite3.connect(self.database) as conn:
            conn.row_factory = self.row_factory
            cursor = conn.cursor()
            cursor.execute("select count(*) as alldirty from contacts where dirty=1")
            return cursor.fetchone()

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

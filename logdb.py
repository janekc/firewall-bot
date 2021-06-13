import os
import sqlite3
from typing import Optional, List
from datetime import date


class DBManager:
    """
    TODO: autoincrement id in logfiles table
    """
    def __init__(self, db_path):
        self.db = sqlite3.connect(db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._execute('''CREATE TABLE IF NOT EXISTS ipcount
                        (ip TEXT PRIMARY KEY,
                         blockshour INTEGER,
                         time INTEGER)''')
        self.db.execute(
                '''CREATE TABLE IF NOT EXISTS logfiles
                (id INTEGER PRIMARY KEY,
                startdate INTEGER,
                bytecursor INTEGER)''')

    def _execute(self, statement, args=()):
        with self.db:
            return self.db.execute(statement, args)

    def store_mailcount(self, ip, blockshour, timestamp):
        self._execute('REPLACE INTO ipcount VALUES (?,?,?)', (ip, blockshour, timestamp))

    def get_mailuser(self, key):
        row = self._execute(
            'SELECT * FROM ipcount WHERE ip=?',
            (key,),
        ).fetchone()
        return row['date'] if row else None
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
                         time INTEGER,
                         coutry TEXT,
                         city TEXT
                         )''')

    def _execute(self, statement, args=()):
        with self.db:
            return self.db.execute(statement, args)

    def store_blockcount(self, ip, blockshour, timestamp, country, city):
        self._execute('REPLACE INTO ipcount VALUES (?,?,?,?,?)', (ip, blockshour, timestamp, country, city))

    def get_blockcount(self, key):
        row = self._execute(
            'SELECT * FROM ipcount WHERE ip=?',
            (key,),
        ).fetchone()
        return row if row else None
    
    def get_allblockcount(self):
        alld = self._execute('SELECT * FROM ipcount')
        return alld
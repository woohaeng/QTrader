import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.sql import text
from database.config import *

class DBHandler:
    def get_connection(self):
        if self.connection.closed:
            self.connection = self.engine.connect()
        return self.connection

    def __init__(self, DB_NAME=DB_INFO):
        dialect_str = 'mysql+pymysql://{user}:{password}@{host}:{port}/{db}'.format(**DB_NAME)
        self.engine = create_engine(dialect_str, echo=False, isolation_level="READ COMMITTED")
        self.connection = self.engine.connect()

    def execute(self, con, stmt, param=None):
        con = con if con else self.get_connection()
        con = con if isinstance(con, type(self.connection)) else con.connection

        result_proxy = None
        if param is None:
            result_proxy = con.execute(stmt)
        elif isinstance(param, dict):
            result_proxy = con.execute(stmt, **param)
        elif isinstance(param, list):
            result_proxy = con.execute(stmt, *param)

        return result_proxy

    def retrive_stmt(self, stmt: text, param=None, transaction=None):
        df = None
        con = transaction
        con = con if con else self.get_connection()
        con = con if isinstance(con, type(self.connection)) else con.connection

        df = None
        result_proxy = self.execute(con, stmt, param)
        rows = result_proxy.fetchall()
        df = pd.DataFrame(rows)
        if len(rows):
            df.columns = rows[0].keys()
        result_proxy.close()

        return df

    def execute_stmt(self, stmt: text, param=None, transaction=None):
        rowcount = -1
        con = transaction
        con = con if con else self.get_connection()
        con = con if isinstance(con, type(self.connection)) else con.connection

        result_proxy = self.execute(con, stmt, param)
        rowcount = result_proxy.rowcount
        result_proxy.close()

        return rowcount
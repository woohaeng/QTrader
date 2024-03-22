import json
import datetime
from io import StringIO
from sqlalchemy.sql import text
from database.DB_Handler import DBHandler

class Database:
    def __init__(self, logging) :
        self.dbHandler = DBHandler()
        self.logging = logging
        self.prefix = "[Database] "

    def select_trading_info(self, account_no):
        self.logging(self.prefix + "select_trading_info()")

        try:
            # stmt = text(f"SELECT * FROM trading_info WHERE account_no = {account_no} AND expire_yn = 'N' ORDER BY magic_no")
            stmt = text(f"SELECT a.*, b.start_date, b.start_price, b.last_price, b.degree, b.contract, b.release_date "
                        f" FROM trading_info a LEFT OUTER JOIN trading_info_status b "
                        f"  ON a.account_no = b.account_no AND a.magic_no = b.magic_no AND b.contract is not null "
                        f"WHERE a.account_no = {account_no} AND a.expire_yn = 'N' ORDER BY a.magic_no")
            result = self.dbHandler.retrive_stmt(stmt)

        except Exception as error:
            self.logging('[Exception] {} in select_trading_info()'.format(error))

        return result

    def select_trading_info_status(self, account_no, magic_no):
        self.logging(self.prefix + "select_trading_info_status()")

        try:
            stmt = text(f"SELECT * FROM trading_info_status WHERE account_no = {account_no} AND magic_no = {magic_no}")
            result = self.dbHandler.retrive_stmt(stmt)

        except Exception as error:
            self.logging('[Exception] {} in select_trading_info()'.format(error))

        return result

    def insert_trading_info_status(self, account_no, magic_no, start_price, contract):
        self.logging(self.prefix + "insert_trading_info_status()")

        try:
            stmt = f"REPLACE INTO trading_info_status (account_no, magic_no, start_date, start_price, " \
                   f"last_price, `degree`, contract, release_date) " \
                   f"VALUES ({account_no}, {magic_no}, NOW(), {start_price}, '{start_price}', 0, {contract}, null)"
            self.dbHandler.execute(None, stmt)

        except Exception as error:
            self.logging('[Exception] {} in select_trading_info()'.format(error))

    def update_trading_info_status(self, account_no, magic_no, last_price, contract):
        self.logging(self.prefix + "update_trading_info_status()")

        try:
            stmt = f"UPDATE trading_info_status SET last_price = {last_price}, degree = degree + 1, " \
                   f"`contract` = {contract} WHERE account_no = {account_no} AND magic_no = {magic_no}"
            self.dbHandler.execute(None, stmt)

        except Exception as error:
            self.logging('[Exception] {} in select_trading_info()'.format(error))

    def delete_trading_info_status(self, account_no, magic_no, releaseDate):
        self.logging(self.prefix + "delete_trading_info_status()")

        try:
            stmt = f"UPDATE trading_info_status SET start_date = null, start_price = 0, last_price = 0, " \
                   f"last_price = 0, degree = 0, contract = 0, release_date = '{releaseDate}' " \
                   f"WHERE account_no = {account_no} AND magic_no = {magic_no}"
            self.dbHandler.execute(None, stmt)

        except Exception as error:
            self.logging('[Exception] {} in select_trading_info()'.format(error))

    def insert_trading_history(self, main):
        self.logging(self.prefix + "insert_trading_history()")

        if len(main.df_holding) == 0 and len(main.df_history) == 0:
            return

        try:
            count = 0
            columns = "account_no,magic_no,order_no,open_time,order_type,order_lots,symbol,open_price,close_time,close_price,commission,order_swap,order_profit"
            stmt = "REPLACE INTO `trading_history` (" + columns + ") VALUES "
            for i in range(len(main.df_holding)):
                df = main.df_holding.iloc[i]

                magic_no = 0
                symbol = ""
                for j in range(len(main.mtg)):
                    if main.mtg[j].code in df['종목코드']:
                        symbol = main.mtg[j].symbol
                        magic_no = main.mtg[j].magic_no
                        break

                stmt += "," if count > 0 else ""
                stmt += "("
                stmt += main.sAccNo + ","
                stmt += str(magic_no) + ","
                stmt += "0,"
                stmt += f"(SELECT start_date FROM trading_info_status WHERE account_no = {main.sAccNo}" \
                        f" AND magic_no = {magic_no} AND contract > 0),"
                stmt += "'SELL'," if df['매도수구분'] == 1 else "'BUY',"
                stmt += str(int(df['수량'])) + ","
                stmt += "'" + symbol + "',"
                stmt += str(df['평균단가']) + ","
                stmt += "null,"
                stmt += "null" + ","
                stmt += str(df['수수료']) + ","
                stmt += "0,"
                stmt += str(df['평가손익'])
                stmt += ")\r\n"
                count += 1

            for i in range(len(main.df_history)):
                df = main.df_history.iloc[i]

                magic_no = 0
                symbol = ""
                for j in range(len(main.mtg)):
                    if main.mtg[j].code in df['종목코드']:
                        symbol = main.mtg[j].symbol
                        magic_no = main.mtg[j].magic_no
                        break

                stmt += "," if count > 0 else ""
                stmt += "("
                stmt += main.sAccNo + ","
                stmt += str(magic_no) + ","
                stmt += df['주문번호'] + ","
                stmt += "'" + df['매입일자'] + "',"
                stmt += "'SELL'," if df['매도수구분'] == 1 else "'BUY',"
                stmt += str(int(df['수량'])) + ","
                stmt += "'" + symbol + "',"
                stmt += str(df['매입표시가격']) + ","
                stmt += "'" + df['체결시간'] + "',"
                stmt += str(df['청산가격']) + ","
                stmt += str(df['수수료']) + ","
                stmt += "0,"
                stmt += str(df['청산손익'])
                stmt += ")\r\n"
                count += 1

            delete_stmt = f"DELETE FROM `trading_history` WHERE account_no = {main.sAccNo} AND close_time is NULL"

            with self.dbHandler.engine.begin() as transaction:
                self.dbHandler.execute_stmt(delete_stmt, None, transaction)
                self.dbHandler.execute_stmt(stmt, None, transaction)

        except Exception as error:
            self.logging('[Exception] {} in insert_trading_history()'.format(error))

    def insert_trading_log(self, main):
        self.logging(self.prefix + "insert_trading_log()")

        now = datetime.datetime.now()
        stime = now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0)

        equity = 0
        if len(main.df_summary) > 0:
            equity = main.df_summary['예탁자산평가'][0]

        try:
            columns = "account_no,magic_no,time,symbol,code, close,equity,open_lots,open_profit"
            stmt = "REPLACE INTO `trading_logs` (" + columns + ") VALUES "

            for j in range(len(main.mtg)):
                mtg = main.mtg[j]

                df = main.df_holding[main.df_holding['종목코드'].str.contains(mtg.code)]
                if len(df) > 0:
                    df = df.iloc[0]
                    stmt += "," if j > 0 else ""
                    stmt += "("
                    stmt += main.sAccNo + ","
                    stmt += str(mtg.magic_no) + ","
                    stmt += "'" + str(stime) + "',"
                    stmt += "'" + mtg.symbol + "',"
                    stmt += "'" + mtg.code + "',"
                    stmt += str(df['현재가격']) + ","
                    stmt += str(equity) + ","
                    stmt += str(int(df['수량'])) + ","
                    stmt += str(df['평가손익'])
                    stmt += ")\r\n"
                else:
                    stmt += "," if j > 0 else ""
                    stmt += "("
                    stmt += main.sAccNo + ","
                    stmt += str(mtg.magic_no) + ","
                    stmt += "'" + str(stime) + "',"
                    stmt += "'" + mtg.symbol + "',"
                    stmt += "'" + mtg.code + "',"
                    stmt += "0" + ","
                    stmt += str(equity) + ","
                    stmt += "0" + ","
                    stmt += "0"
                    stmt += ")\r\n"

            self.dbHandler.execute(None, stmt)

        except Exception as error:
            self.logging('[Exception] {} in insert_trading_log()'.format(error))

    def insert_test_info(self, main):
        self.logging(self.prefix + "insert_test_info()")

        try:
            stmt = f"INSERT INTO test_info (ea_name, symbol, timeunit, parameters, from_date, to_date, init_deposit, " \
                   f"total_net_profit, max_drawdown, total_trade, profit_trade) " \
                   f"VALUES ('키움CME', '{main.mtg.config['SYMBOL']}', {main.mtg.config['TIME_UNIT']}, " \
                   f"'{json.dumps(main.mtg.config)}', '{main.df_cur_agg.index[0]}', '{main.df_cur_agg.index[-1]}', " \
                   f"{main.init_equity}, {main.profit}, {main.mdd}, {main.total_trade}, {main.profit_trade})"
            result = self.dbHandler.execute(None, stmt)

            return result.lastrowid

        except Exception as error:
            self.logging('[Exception] {} in insert_test_info()'.format(error))

    def insert_test_logs(self, df_mlogs, lastrowid):
        self.logging(self.prefix + "insert_test_logs()")

        try:
            csv_data  = StringIO()
            df_mlogs.to_csv(csv_data, index=False)

            stmt = f"INSERT INTO `test_logs` (test_id, logs) VALUES ({lastrowid}, '{csv_data.getvalue()}')"
            self.dbHandler.execute(None, stmt)

        except Exception as error:
            self.logging('[Exception] {} in insert_test_logs()'.format(error))
import os
from Martingale import *
from Database import *


class TraderSimul:
    def __init__(self):
        self.mtg = None
        self.df_cur_agg = pd.DataFrame()
        self.df_cur = pd.DataFrame()
        self.db = Database(self.logging)

        self.history = []
        self.df_order = pd.DataFrame(columns=['type', 'lots', 'price', 'commission', 'swap', 'profit'])
        self.signal = None
        self.init_equity = 100000
        self.equity = self.init_equity
        self.profit = 0
        self.mdd = 0
        self.total_trade = 0
        self.profit_trade = 0

    def loadData(self, filename):
        parquetfile = filename.replace(".csv", ".parquet")
        if os.path.exists(parquetfile):
            df = pd.read_parquet(parquetfile)
        else:
            df = pd.read_csv(filename, dtype={'<DTYYYYMMDD>': str, '<TIME>': str},
                             usecols=['<DTYYYYMMDD>', '<TIME>', '<OPEN>', '<HIGH>', '<LOW>', '<CLOSE>'])

            df.index = pd.to_datetime(df['<DTYYYYMMDD>'] + df['<TIME>'])
            df.index.name = 'time'
            df.drop(['<DTYYYYMMDD>', '<TIME>'], inplace=True, axis=1)
            df.columns = ['open', 'high', 'low', 'close']
            df.index = df.index.shift(9, freq='H')
            df.to_parquet(parquetfile, compression='gzip')

        return df

    def getOrderInfo(self, mtg):
        # 현재 상태 확인
        trade = MyTrade()

        close = self.df_cur.iloc[-1]['Close']
        point = self.mtg.getPipPoint()

        self.df_order['profit'] = self.df_order.apply(lambda x: (close - x['price']) * x['lots'] / point \
            if x['type'] == self.mtg.OP_BUY else (x['price'] - close) * x['lots'] / point, axis=1)

        trade.orderType = self.df_order.iloc[-1]['type']
        trade.totalProfit = self.df_order['profit'].sum()
        trade.startDate = self.df_cur.index[-1]
        trade.startPrice = self.df_order.iloc[0]['price']
        trade.lastPrice = self.df_order.iloc[-1]['price']
        trade.degree = len(self.df_order) - 1
        trade.contract = self.df_order['lots'].sum()
        trade.releaseDate = self.mtg.releaseDate
        trade.price = close

        mtg.trade = trade

    def openCheck(self):
        # 포지션 진입 체크
        # self.logging('Start openCheck()')

        self.mtg.df_cur = self.df_cur

        signal = self.mtg.checkForOpen()

        if signal == self.mtg.OP_SELL or signal == self.mtg.OP_BUY:
            lots = self.mtg.config["ORDER_LOTS"]
            df_new = pd.DataFrame([{'type': signal,
                         'lots': lots,
                         'price': self.df_cur.iloc[-1]['Close'],
                         'commission': lots * 2,
                         'swap': 0,
                         'profit': 0}])
            self.df_order = pd.concat([self.df_order, df_new], axis=0)
            self.signal = signal

        history = {'time': self.df_cur.index[-1],
                   'close': self.df_cur.iloc[-1]['Close'],
                   'equity': self.equity,
                   'openLots': 0,
                   'openProfit': 0,
                   'commission': 0,
                   'swap': 0}
        self.history.append(history)

        # self.logging('Finished openCheck()')

    def closeCheck(self):
        # 포지션 청산 체크
        # self.logging('Start closeCheck()')

        # 포지션 청산 체크
        self.getOrderInfo(self.mtg)

        if self.mtg.trade is not None:
            self.mtg.df_cur = self.df_cur
            self.mtg.close = self.df_cur.iloc[-1]['Close']

            signal = self.mtg.checkForClose()

            if signal == self.mtg.OP_CLOSE:  # 청산
                self.equity = self.equity + self.mtg.trade.totalProfit
                print("date:", self.df_cur.index[-1], ", equity:", round(self.equity, 1),
                      ", profit:", round(self.mtg.trade.totalProfit, 1),
                      ", degree:", self.mtg.trade.degree)

                self.total_trade += 1
                if self.mtg.trade.totalProfit > 0:
                    self.profit_trade += 1

                self.mtg.trade = MyTrade()
                self.mtg.trade.totalProfit = 0
                self.mtg.trade.contract = 0
                self.df_order = pd.DataFrame(columns=self.df_order.columns)
                self.signal = None

            elif signal == self.mtg.OP_SELL or signal == self.mtg.OP_BUY:  # 추가 주문
                lots = self.mtg.getNextOrderLots()
                df_new = pd.DataFrame([{'type': signal,
                             'lots': lots,
                             'price': self.df_cur.iloc[-1]['Close'],
                             'commission': lots * 2,
                             'swap': 0,
                             'profit': 0}])
                self.df_order = pd.concat([self.df_order, df_new], axis=0)
                self.signal = signal

        history = {'time': self.df_cur.index[-1],
                   'close': self.df_cur.iloc[-1]['Close'],
                   'equity': self.equity + self.mtg.trade.totalProfit,
                   'openLots': self.mtg.trade.contract,
                   'openProfit': self.mtg.trade.totalProfit,
                   'commission': self.mtg.trade.contract * 2,
                   'swap': 0}

        self.history.append(history)

        # self.logging('Finished closeCheck()')

    def logging(self, strData):
        print(strData)

    def get_compute_mdd(self, mlogs):
        mlog_s = mlogs[0]
        mdds = []
        for mlog in mlogs:
            cur_mdd = mlog / mlog_s - 1
            if cur_mdd > 0:
                cur_mdd = 0
                mlog_s = mlog

            mdds.append(abs(cur_mdd) * 100)

        return mdds

    def main(self):
        df_all = self.loadData("rawdata\eurusd.csv")
        df_all['time'] = pd.to_datetime(df_all['time'])
        df_all.set_index('time', inplace=True)

        params = json.loads('''{"MEMO": "CME", "SYMBOL": "EURUSD", "CODE": "M6E", "ORDER_LOTS": 1, "LOTS_MULTIPLE": 1.5, 
         "MINIMUM_PROFIT": 67, "MAXIMUM_PRICE_SLIPPAGE": 3, "FIRST_TRAILING_STEP": 100, "OTHER_TRAILING_STEP": 50, 
         "LIMIT_MAX_DEGREE": 10, "LOSS_CUT_PIPS": 800, "LOSS_CUT_DAYS": 300, "HOLD_DAYS_AFTER_LOSS_CUT": 30, 
         "ALGORITHM_TYPE": "ALGO_DMI", "DMI_PERIOD": 12, "MACD_LONG_PERIOD": 26, "MACD_SHORT_PERIOD": 12, 
         "MACD_SIGNAL_PERIOD": 9, "CCI_PERIOD": 14, "CCI_RANGE": 80, "CHECK_ADX_IND": true, "CHECK_RSI_IND": true, 
         "CHECK_LONG_EMA_IND": false, "CHECK_SHORT_EMA_IND": false, "ADX_ALLOW_LEVEL": 15, "LONG_MA_PERIOD": 200, 
         "SHORT_MA_PERIOD": 3, "RSI_ALLOW_LEVEL": 40}''')

        self.mtg = Martingale(self, 0, params)
        self.mtg.real_mode = False

        time_unit = self.mtg.config['TIME_UNIT']

        dict_agg = dict(close='last', open='first', high='max', low='min')
        grouper = pd.Grouper(freq=f'{time_unit}min', closed='right', label='right')
        self.df_cur_agg = df_all.groupby(grouper).agg(dict_agg)
        self.df_cur_agg.dropna(inplace=True)
        self.df_cur_agg.columns = ['Open', 'High', 'Low', 'Close']

        # print(self.df_cur_agg)

        for i in range(500, len(self.df_cur_agg)):
            self.df_cur = self.df_cur_agg.iloc[i - 500:i].copy()

            if self.signal is None:
                self.openCheck()
            else:
                self.closeCheck()

        self.mtg.showCheckOpen()

    def save(self):
        df_mlogs = pd.DataFrame(self.history)

        self.profit = round(df_mlogs.iloc[-1]['equity'] - self.init_equity, 1)
        df_mdd = self.get_compute_mdd(df_mlogs["equity"].values)
        self.mdd = round(max(df_mdd), 4)

        lastrowid = self.db.insert_test_info(self)
        self.db.insert_test_logs(df_mlogs, lastrowid)

        print(f"test_id = {lastrowid}")
        print(f"profit = {self.profit}, mdd = {self.mdd}, total trade = {self.total_trade}")


if __name__ == "__main__":
    simul = TraderSimul()
    simul.main()
    simul.save()

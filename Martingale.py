import pandas as pd
import talib
import json
import datetime
from dataclasses import dataclass


@dataclass
class MyTrade:
    orderType: int = None
    totalProfit: float = None
    startDate: str = None
    startPrice: float = None
    lastPrice: float = None
    degree: int = None
    contract: int = None
    releaseDate: str = None
    price: float = None


class Martingale:
    def __init__(self, main, magic_no, params):
        self.main = main

        self.OP_BUY = 1
        self.OP_SELL = 2
        self.OP_CLOSE = 3
        # self.DAY_SECONDS = 86400

        # self.config = json.loads('{"SYMBOL": "NONE", "ORDER_LOTS": 0.03, "LOTS_MULTIPLE": 1.5, "MINIMUM_PROFIT": 2, ' \
        # profit : 2$ / 3 * 100 = 67$
        self.config = json.loads(
            '{"SYMBOL": "NONE", "CODE": "NONE", "TIME_UNIT": 15, "ORDER_LOTS": 1, "LOTS_MULTIPLE": 2, "MINIMUM_PROFIT": 67, ' \
            '"MAXIMUM_PRICE_SLIPPAGE": 3, "FIRST_TRAILING_STEP": 100, "OTHER_TRAILING_STEP": 50, ' \
            '"LIMIT_MAX_DEGREE": 10, "LOSS_CUT_PIPS": 800, "LOSS_CUT_DAYS": 300, "HOLD_DAYS_AFTER_LOSS_CUT": 30, ' \
            '"ALGORITHM_TYPE": "ALGO_DMI", "DMI_PERIOD": 12, "MACD_LONG_PERIOD": 26, ' \
            '"MACD_SHORT_PERIOD": 12, "MACD_SIGNAL_PERIOD": 9, "CCI_PERIOD": 14, "CCI_RANGE": 80, ' \
            '"CHECK_ADX_IND": true, "CHECK_RSI_IND": true, "CHECK_LONG_EMA_IND": true, ' \
            '"CHECK_SHORT_EMA_IND": true, "CHECK_ENVELOPES_IND": false, "ADX_ALLOW_LEVEL": 20, ' \
            '"LONG_MA_PERIOD": 200, "SHORT_MA_PERIOD": 3, "ENVELOPES_PERIOD": 200, ' \
            '"ENVELOPES_DEVIATION": 0.5}')

        self.real_mode = False
        self.magic_no = magic_no
        self.symbol = None
        self.code = None
        self.loadConfig(params)
        self.df_cur = pd.DataFrame()
        self.trade = MyTrade()

        self.close = 0
        self.lastOrderTime = None

    def loadConfig(self, params):
        self.symbol = params['SYMBOL']
        self.code = params['CODE']

        for key, value in params.items():
            if self.config.__contains__(key):
                self.config[key] = self.convertValue(value, type(self.config[key]))

    def convertValue(self, value, value_type: str):
        if value in [None, 'None']:
            val = None
        elif isinstance(value, value_type):
            val = value
        else:
            if value_type == str:
                val = str(value)
            elif value_type == int:
                val = eval(value)
            elif value_type == float:
                val = eval(value)
            elif value_type == bool:
                if isinstance(value, str):
                    val = eval(value)
                else:
                    val = bool(value)
            else:
                if isinstance(value, str):
                    val = eval(f"{value_type}({value!r})")
                else:
                    val = value
        return val

    def getUnitTime(self, inTime):
        if inTime is None:
            return None

        outTime = inTime.replace(minute=inTime.minute // self.config["TIME_UNIT"] * self.config["TIME_UNIT"],
                                 second=0, microsecond=0)

        return outTime

    def getPipPoint(self):
        if self.symbol in ('EURUSD', 'AUDUSD', 'GBPUSD', 'CADUSD', 'CHFUSD'):
            return 0.0001

        return 0

    def checkDmiSignal(self):
        tradingSignal = None

        pdi = talib.PLUS_DI(self.df_cur['High'], self.df_cur['Low'], self.df_cur['Close'], self.config['DMI_PERIOD'])
        mdi = talib.MINUS_DI(self.df_cur['High'], self.df_cur['Low'], self.df_cur['Close'], self.config['DMI_PERIOD'])

        diPlusBfr, diPlus = pdi[-2], pdi[-1]
        diMinusBfr, diMinus = mdi[-2], mdi[-1]

        # Golden Cross or Dead Cross
        if diPlusBfr < diMinusBfr and diPlus > diMinus:
            tradingSignal = self.OP_BUY
            self.main.logging('■ checkDmiSignal() : BUY ' + self.code)
        elif diPlusBfr > diMinusBfr and diPlus < diMinus:
            tradingSignal = self.OP_SELL
            self.main.logging('■ checkDmiSignal() : SELL ' + self.code)

        return tradingSignal

    def checkMacdSignal(self):
        tradingSignal = None

        macd = talib.MACD(self.df_cur['Close'], self.config['MACD_SHORT_PERIOD'], self.config['MACD_LONG_PERIOD'],
                          self.config['MACD_SIGNAL_PERIOD'])

        mainBfr, main = macd['macd'][-2], macd['macd'][-1]
        signalBfr, signal = macd['macdsignal'][-2], macd['macdsignal'][-1]

        # Golden Cross or Dead Cross
        if mainBfr < signalBfr and main > signal:
            tradingSignal = self.OP_BUY
        elif mainBfr > signalBfr and main < signal:
            tradingSignal = self.OP_SELL

        return tradingSignal

    def checkOpen(self, orderType):
        # 거래 시작 : 15븐봉 완료시
        adx = talib.ADX(self.df_cur['High'], self.df_cur['Low'], self.df_cur['Close'], self.config['DMI_PERIOD'])[-1] \
            if self.config['CHECK_ADX_IND'] else 0
        rsi = talib.RSI(self.df_cur['Close'], self.config['DMI_PERIOD'])[-1] \
            if self.config['CHECK_RSI_IND'] else 0
        maLongTrend = talib.MA(self.df_cur['Close'], self.config['LONG_MA_PERIOD'])[-1] \
            if self.config['CHECK_LONG_EMA_IND'] else 0
        maShortTrendBfr = talib.MA(self.df_cur['Close'], self.config['SHORT_MA_PERIOD'])[-2] \
            if self.config['CHECK_SHORT_EMA_IND'] else 0
        maShortTrend = talib.MA(self.df_cur['Close'], self.config['SHORT_MA_PERIOD'])[-1] \
            if self.config['CHECK_SHORT_EMA_IND'] else 0
        # envlUpper = iCustom(NULL, 0, "Envelopes", ENVELOPES_PERIOD, 0, MODE_EMA, PRICE_CLOSE, ENVELOPES_DEVIATION, 0, 1) \
        #     if self.config['CHECK_ENVELOPES_IND'] else 0
        # envlLower = iCustom(NULL, 0, "Envelopes", ENVELOPES_PERIOD, 0, MODE_EMA, PRICE_CLOSE, ENVELOPES_DEVIATION, 1, 1) \
        #     if self.cofngi['CHECK_ENVELOPES_IND'] else 0

        # ADX 가 ADX_ALLOW_LEVEL보다 커야 거래
        if self.config['CHECK_ADX_IND'] and adx < self.config['ADX_ALLOW_LEVEL']: return None

        if orderType == self.OP_BUY:
            # 종가가 LONG EMA 보다 크면 매수
            if self.config['CHECK_LONG_EMA_IND'] and self.df_cur['Close'][-1] < maLongTrend: return None
            # SHORT EMA 가 상승시 매수
            if self.config['CHECK_SHORT_EMA_IND'] and maShortTrendBfr > maShortTrend: return None
            # RSI가 50 이하에서 매수
            if self.config['CHECK_RSI_IND'] and rsi > 50: return None
            # Envelopes Upper 이하에서 매수
            # if (self.config['CHECK_ENVELOPES_IND'] and self.df_cur['Close'][-1] > envlUpper): return None

            self.main.logging('■ checkOpen() : BUY ' + self.code)
        else:
            # 종가가 LONG EMA 보다 작으면 매도
            if self.config['CHECK_LONG_EMA_IND'] and self.df_cur['Close'][-1] > maLongTrend: return None
            # SHORT EMA 가 하락시 매도
            if self.config['CHECK_SHORT_EMA_IND'] and maShortTrendBfr < maShortTrend: return None
            # RSI가 50 이상에서 매수
            if self.config['CHECK_RSI_IND'] and rsi < 50: return None
            # Envelopes Lower이상에서 매도
            # if (self.config['CHECK_ENVELOPES_IND'] and self.df_cur['Close'][-1] < envlLower): return None

            self.main.logging('■ checkOpen() : SELL ' + self.code)

        return orderType

    def checkForOpen(self):
        now = self.getUnitTime(datetime.datetime.now())
        lastTime = self.getUnitTime(self.lastOrderTime)

        if lastTime is not None and lastTime == now: return None
        if self.trade.releaseDate is not None and self.trade.releaseDate > now: return None

        tradingSignal = None

        if self.config['ALGORITHM_TYPE'] == "ALGO_DMI":
            tradingSignal = self.checkDmiSignal()
            if tradingSignal == self.OP_BUY or tradingSignal == self.OP_SELL:
                tradingSignal = self.checkOpen(self.OP_BUY)
        elif self.config['ALGORITHM_TYPE'] == "ALGO_MACD":
            tradingSignal = self.checkMacdSignal()
            if tradingSignal == self.OP_BUY or tradingSignal == self.OP_SELL:
                tradingSignal = self.checkOpen(self.OP_BUY)

        if tradingSignal is not None:
            self.lastOrderTime = datetime.datetime.now()

        # if self.code == 'MSF':  # TEST
        #     return self.OP_BUY

        return tradingSignal

    def addNewOrder(self):
        now = self.getUnitTime(datetime.datetime.now())
        lastTime = self.getUnitTime(self.lastOrderTime)

        if lastTime is not None and lastTime == now: return None
        if self.trade.releaseDate is not None and self.trade.releaseDate > now: return None

        myPoint = self.getPipPoint()

        if self.trade.degree == 0:
            if self.trade.orderType == self.OP_BUY:
                if self.trade.startPrice - self.config['FIRST_TRAILING_STEP'] * myPoint > self.close \
                        and self.checkOpen(self.OP_BUY):
                    self.lastOrderTime = datetime.datetime.now()
                    return self.OP_BUY
            elif self.trade.orderType == self.OP_SELL:
                if self.trade.startPrice + self.config['FIRST_TRAILING_STEP'] * myPoint < self.close \
                        and self.checkOpen(self.OP_SELL):
                    self.lastOrderTime = datetime.datetime.now()
                    return self.OP_SELL
        else:
            if self.trade.orderType == self.OP_BUY:
                if self.trade.startPrice - self.config['OTHER_TRAILING_STEP'] * myPoint > self.close \
                        and self.checkOpen(self.OP_BUY):
                    self.lastOrderTime = datetime.datetime.now()
                    return self.OP_BUY
            elif self.trade.orderType == self.OP_SELL:
                if self.trade.startPrice + self.config['OTHER_TRAILING_STEP'] * myPoint < self.close \
                        and self.checkOpen(self.OP_SELL):
                    self.lastOrderTime = datetime.datetime.now()
                    return self.OP_SELL

        return None

    def checkForClose(self):
        myPoint = self.getPipPoint()

        # 익절(현재 수익 > 기준 수익)
        if self.trade.totalProfit > self.config['MINIMUM_PROFIT']:
            self.lastOrderTime = datetime.datetime.now()
            return self.OP_CLOSE

        # 차수 초과시 손절
        if self.trade.totalProfit < 0:
            bOverDue = (datetime.datetime.now() - self.trade.startDate).days >= self.config['LOSS_CUT_DAYS']

            if self.trade.orderType == self.OP_BUY \
                    and self.trade.startPrice - self.config['LOSS_CUT_PIPS'] * myPoint > self.close or bOverDue:
                self.lastOrderTime = datetime.datetime.now()
                return self.OP_CLOSE
            elif self.trade.orderType == self.OP_SELL \
                    and self.trade.startPrice + self.config['LOSS_CUT_PIPS'] * myPoint < self.close or bOverDue:
                self.lastOrderTime = datetime.datetime.now()
                return self.OP_CLOSE

        # 추가 진입 체크
        if self.trade.totalProfit < 0 and self.trade.degree < self.config['LIMIT_MAX_DEGREE'] - 1:
            self.addNewOrder()

    def getNextOrderLots(self):
        nowlots = self.trade.contract
        nextLots = int(nowlots * self.config['LOTS_MULTIPLE'])
        addLots = nextLots - nowlots

        return addLots if addLots > 0 else 1

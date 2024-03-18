import numpy as np
from datetime import datetime
from Martingale import *
from Database import *

class TraderSimul:
    def __init__(self):
        super().__init__()

        self.mtg = Martingale(self, row['magic_no'], params)

        self.db = Database(self.logging)
        self.loadMartingaleInfo()

        self.openLoginPannel()

    def timerUpdate(self):
        self.timer.stop()

        try:
            if self.jobStep == 0:  # 새로고침
                self.lbSave.setStyleSheet("")
                self.lbRefresh.setStyleSheet("background-color: rgb(255, 200, 255);")
                self.jangoRefresh()
                self.orderRefresh()
                self.holdingRefresh()
                self.historyRefresh()
                self.jobStep += 1
            elif self.jobStep == 1:  # 시그널 체크
                self.lbRefresh.setStyleSheet("")
                self.lbOpen.setStyleSheet("background-color: rgb(255, 200, 255);")
                now = datetime.datetime.now()
                stime = now.replace(minute=now.minute // 15 * 15, second=0, microsecond=0)

                if self.checkTime != stime:
                    self.applyTrade()
                    self.openCheck()
                    self.checkTime = stime

                self.jobStep += 1
            elif self.jobStep == 2:  # 청산 체크
                self.lbOpen.setStyleSheet("")
                self.lbClose.setStyleSheet("background-color: rgb(255, 200, 255);")
                self.applyTrade()
                self.closeCheck()
                self.jobStep += 1
            elif self.jobStep == 3:  # DB 저장
                self.lbClose.setStyleSheet("")
                self.lbSave.setStyleSheet("background-color: rgb(255, 200, 255);")
                self.db.insert_trading_log(self)
                self.db.insert_trading_history(self)
                self.jobStep = 0
            else:
                self.jobStep += 1

        except Exception as error:
            self.logging('[Exception] {} in timerUpdate()'.format(error))

        self.timer.start()

    def getOrderInfo(self, mtg):
        # 현재 상태 확인
        trade = MyTrade()

        result = self.db.select_trading_info_status(self.sAccNo, mtg.magic_no).iloc[0]

        df_holding = self.df_holding[self.df_holding['종목코드'].str.contains(mtg.code)]
        if len(df_holding) > 0:
            trade.totalProfit = df_holding['평가손익'].sum()
            trade.orderType = df_holding.iloc[0]['매도수구분']
            trade.orderType = mtg.OP_SELL if trade.orderType == 1 else mtg.OP_BUY
            trade.price = df_holding.iloc[0]['현재가격']

            trade.startDate = result['start_date']
            trade.startPrice = result['start_price']
            trade.lastPrice = result['last_price']
            trade.degree = result['degree']
            trade.contract = int(df_holding.iloc[0]['수량'])
            trade.releaseTime = result['release_date']
        else:
            return None

        mtg.trade = trade

    def openCheck(self):
        self.logging('Start openCheck()')

        # 포지션 진입 체크
        for mtg_no in range(len(self.mtg)):
            mtg = self.mtg[mtg_no]

            status = self.tbAlgorithm.item(mtg_no, 3)
            if status.text() == "BUY" or status.text() == "SELL":
                continue

            mtg.df_cur = self.df_cur

            signal = mtg.checkForOpen()

            if signal == mtg.OP_SELL:
                sCode = self.getNextCode(mtg.code)
                self.logging(f'■ 신규 주문: 매도, #{mtg.magic_no}, {sCode}')
                self.orderOpen(1, sCode, 1, "0", "0", "1")  # 시장가 매도
            elif signal == mtg.OP_BUY:
                sCode = self.getNextCode(mtg.code)
                self.logging(f'■ 신규 주문: 매수, #{mtg.magic_no}, {sCode}')
                self.orderOpen(2, sCode, 1, "0", "0", "1")  # 시장가 매수

        self.logging('Finished openCheck()')

    def closeCheck(self):
        # 포지션 청산 체크
        self.logging('Start closeCheck()')

        # 포지션 진입 체크
        for mtg_no in range(len(self.mtg)):
            mtg = self.mtg[mtg_no]

            status = self.tbAlgorithm.item(mtg_no, 3)
            if status.text() != "BUY" and status.text() != "SELL":
                continue

            self.getOrderInfo(mtg)
            if mtg.trade is None:
                continue

            if mtg.trade.totalProfit < 0:
                # 차트 조회
                self.df_cur = pd.DataFrame()

                if self.df_cur.empty:
                    continue

                mtg.df_cur = self.df_cur
                mtg.close = self.df_cur.iloc[-1]['Close']
            else:
                df_holding = self.df_holding[self.df_holding['종목코드'].str.contains(mtg.code)]
                mtg.close = df_holding.iloc[0]['현재가격']

            signal = mtg.checkForClose()

            if signal == mtg.OP_CLOSE:  # 청산
                df = self.df_holding[self.df_holding['종목코드'].str.contains(mtg.code)]
                if len(df) == 0:
                    continue

                signal = mtg.OP_SELL if df.iloc[0]['매도수구분'] == 1 else mtg.OP_BUY
                sCode = df.iloc[0]['종목코드']

                if signal == mtg.OP_SELL:
                    self.logging(f'■ 청산 주문: 매도 -> 매수, #{mtg.magic_no}, {sCode}')
                    self.orderOpen(2, sCode, mtg.trade.contract, "0", "0", "1")  # 시장가 매도
                elif signal == mtg.OP_BUY:
                    self.logging(f'■ 청산 주문: 매수 -> 매도, #{mtg.magic_no}, {sCode}')
                    self.orderOpen(1, sCode, mtg.trade.contract, "0", "0", "1")  # 시장가 매수
            else:  # 추가 진입
                if signal == mtg.OP_SELL:
                    sCode = self.getNextCode(mtg.code)
                    lots = mtg.getNextOrderLots()
                    self.logging(f'■ 추가 주문: 매도, #{mtg.magic_no}, {sCode}')
                    self.orderOpen(1, sCode, lots, "0", "0", "1")  # 시장가 매도
                elif signal == mtg.OP_BUY:
                    sCode = self.getNextCode(mtg.code)
                    lots = mtg.getNextOrderLots()
                    self.logging(f'■ 추가 주문: 매수, #{mtg.magic_no}, {sCode}')
                    self.orderOpen(2, sCode, lots, "0", "0", "1")  # 시장가 매수

        self.logging('Finished closeCheck()')

    def main(self):

        pass

    def save(self):
        pass

if __name__ == "__main__":
    simul = TraderSimul()
    simul.main()
    simul.save()

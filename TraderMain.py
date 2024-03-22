# import sys
# import time
# import ctypes
import numpy as np
# import threading as tr
# import pandas as pd
import subprocess
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5 import uic
from KFOpenAPI import *
from Martingale import *
from Database import *
from AutoLogin import *

TraderMainForm = uic.loadUiType("trader_main.ui")[0]


class TraderMain(QMainWindow, TraderMainForm):
    def __init__(self):
        super().__init__()
        self.setupUi(self)
        self.initButton()

        self.logCounter = 0
        # self.tr_event_loop = None
        self.timer = QTimer(self)
        self.timer.setInterval(10000)
        self.timer.timeout.connect(self.timerUpdate)
        self.jobStep = 0

        self.kiwoom = KFOpenAPI()
        # self.accountInfo = AccountInfo(self.kiwoom)
        self.sScrNo = self.kiwoom.GetScreenNumber()
        self.sLoginId = 'valfind'
        self.sLoginPwd = 'val1223'
        self.sAccNo = '7018721872'
        self.sAccPwd = "0000"
        self.kiwoom.OnReceiveTrData.connect(self.ReceiveTrData)
        # self.kiwoom.OnReceiveRealData.connect(self.ReceiveRealData)
        self.kiwoom.OnReceiveMsg.connect(self.ReceiveMsg)
        self.kiwoom.OnReceiveChejanData.connect(self.ReceiveChejanData)
        self.kiwoom.OnEventConnect.connect(self.EventConnect)

        self.gbAccount.setTitle("계좌 정보 - " + self.sAccNo)
        header = self.tbAccount.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch)

        self.df_summary = pd.DataFrame()
        self.df_order = pd.DataFrame()
        self.df_holding = pd.DataFrame()
        self.df_history = pd.DataFrame()
        self.df_cur = pd.DataFrame()
        self.checkTime = datetime.datetime.now()

        self.mtg = []

        self.db = Database(self.logging)
        self.loadMartingaleInfo()

        self.openLoginPannel()

    def initButton(self):
        self.actionLogin.setShortcut('Ctrl+L')
        self.actionLogin.setStatusTip('Open Login pannel')
        self.actionLogin.triggered.connect(self.openLoginPannel)

        self.actionLogout.setShortcut('Ctrl+O')
        self.actionLogout.setStatusTip('Disconnect')
        self.actionLogout.triggered.connect(self.disconnect)

        self.actionClose.setShortcut('Ctrl+X')
        self.actionClose.setStatusTip('Close')
        self.actionClose.triggered.connect(self.close)

        self.cbSmryLog.stateChanged.connect(self.showSummary)

        self.pbTest.clicked.connect(self.jangoRefresh)

        # self.pbSetPassword.clicked.connect(self.enterAccountPassword)
        self.pbStart.clicked.connect(self.start)
        self.pbOpenCheck.clicked.connect(self.openCheck)
        self.pbCloseCheck.clicked.connect(self.closeCheck)

        self.pbOrderRefresh.clicked.connect(self.orderRefresh)
        self.pbHoldingRefresh.clicked.connect(self.holdingRefresh)
        self.pbHistoryRefresh.clicked.connect(self.historyRefresh)

    def loadMartingaleInfo(self):
        if self.sAccNo == '':
            return

        self.mtg = []

        result = self.db.select_trading_info(self.sAccNo)

        self.tbAlgorithm.setRowCount(len(result))

        # 순번, 통화쌍, 종목코드, 손익
        for i in range(len(result)):
            row = result.iloc[i].fillna(0)

            params = json.loads(row['parameters'])
            mtg = Martingale(self, row['magic_no'], params)
            mtg.debug_mode = True

            tableItem = QTableWidgetItem(str(row['magic_no']))
            tableItem.setTextAlignment(Qt.AlignCenter)
            self.tbAlgorithm.setItem(i, 0, tableItem)

            # tableItem = QTableWidgetItem(str(row['symbol']))
            # tableItem.setTextAlignment(Qt.AlignCenter)
            # self.tbAlgorithm.setItem(i, 1, tableItem)

            tableItem = QTableWidgetItem(str(mtg.code))
            tableItem.setTextAlignment(Qt.AlignCenter)
            self.tbAlgorithm.setItem(i, 1, tableItem)

            tableItem = QTableWidgetItem("")
            tableItem.setTextAlignment(Qt.AlignCenter)
            self.tbAlgorithm.setItem(i, 2, tableItem)

            tableItem = QTableWidgetItem("READY")
            tableItem.setTextAlignment(Qt.AlignCenter)
            self.tbAlgorithm.setItem(i, 3, tableItem)

            tableItem = QTableWidgetItem(str(row['start_date']) if row['contract'] > 0 else '')
            tableItem.setTextAlignment(Qt.AlignCenter)
            self.tbAlgorithm.setItem(i, 4, tableItem)

            tableItem = QTableWidgetItem(str(row['start_price']) if row['contract'] > 0 else '')
            tableItem.setTextAlignment(Qt.AlignCenter)
            self.tbAlgorithm.setItem(i, 5, tableItem)

            tableItem = QTableWidgetItem(str(row['last_price']) if row['contract'] > 0 else '')
            tableItem.setTextAlignment(Qt.AlignCenter)
            self.tbAlgorithm.setItem(i, 6, tableItem)

            tableItem = QTableWidgetItem(str(int(row['degree'])) if row['contract'] > 0 else '')
            tableItem.setTextAlignment(Qt.AlignCenter)
            self.tbAlgorithm.setItem(i, 7, tableItem)

            tableItem = QTableWidgetItem(str(int(row['contract'])) if row['contract'] > 0 else '')
            tableItem.setTextAlignment(Qt.AlignCenter)
            self.tbAlgorithm.setItem(i, 8, tableItem)

            # header = self.tbAlgorithm.horizontalHeader()
            # header.setSectionResizeMode(QHeaderView.Stretch)

            self.mtg.append(mtg)

        self.tbAlgorithm.show()

    def showSummary(self):
        if self.cbSmryLog.isChecked():
            self.lstLog.hide()
            self.lstSmryLog.show()
        else:
            self.lstLog.show()
            self.lstSmryLog.hide()

    def start(self):
        self.jobStep = 0
        self.timer.start()

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
                    # self.logging('>>> openCheck: ' + stime.strftime('%Y-%m-%d %H:%M'))
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

    def logging(self, strData):
        # 각종 데이터 처리 과정을 메론 로그에 남김
        filename = f'logs\\log_{datetime.datetime.now().strftime("%Y%m%d")}.log'

        if self.logCounter == 0:
            logFile = open(filename, 'a')
            logFile.write('\n\n[{0}] Started Program'.format(time.ctime()))
            logFile.close()

        try:
            if not (isinstance(strData, str)):
                strData = str(strData)

            item_count = self.lstLog.count()
            if item_count >= 500:
                self.lstLog.takeItem(0)

            self.statusBar().showMessage(strData)

            self.lstLog.addItem('[{0:05d}] {1}'.format(self.logCounter, strData))
            self.lstLog.scrollToBottom()

            if strData.startswith("■") or "[Exception]" in strData:
                self.lstSmryLog.addItem('[{0:05d}] {1}'.format(self.logCounter, strData))
                self.lstSmryLog.scrollToBottom()

            logFile = open(filename, 'a')
            logFile.write('\n[{0:05d}] {1}'.format(self.logCounter, strData))
            logFile.close()
            self.logCounter += 1

        except:
            print('logging error.')

    # def Logging(self, strData):
    #     self.logging(strData)

    def openLoginPannel(self):
        if not self.kiwoom.GetConnectState():
            self.logging('Opened Login Pannel')

            subprocess.Popen(["python", "AutoLogin.py", self.sLoginPwd, self.sAccPwd])
            # subprocess.Popen(["conda", "run", "-n", "myQtrd32", "python", "AutoLogin.py", self.sLoginPwd, self.sAccPwd])

            self.kiwoom.CommConnect()

            self.kiwoom.dynamicCall("GetCommonFunc(QString, QString", "ShowAccountWindow", "")
        else:
            # self.accountInfo.SetConnectState(True)
            self.logging('Already Connected!!')

    def disconnect(self):
        if self.kiwoom.GetConnectState():
            self.kiwoom.CommTerminate()
            # self.accountInfo.SetConnectState(False)
            self.logging('Disconnected')
        else:
            # self.accountInfo.SetConnectState(False)
            self.logging('Already Disconnected!!')

        self.logCounter = 0

    def algorithmRefresh(self):
        pass

    def orderRefresh(self):
        # 미체결 종목
        sRQName = '계좌정보조회'
        sTrCode = TrList.OPW['TR_OPW30001']
        sScrNo = self.sScrNo
        try:
            self.logging('Start orderRefresh()')
            self.kiwoom.SetInputValue('계좌번호', self.sAccNo)
            self.kiwoom.SetInputValue('비밀번호', '')
            self.kiwoom.SetInputValue('비밀번호입력매체', '00')
            self.kiwoom.SetInputValue('종목코드', '')
            self.kiwoom.SetInputValue('통화코드', 'USD')
            self.kiwoom.SetInputValue('매도수구분', '')
            errorCode = self.kiwoom.CommRqData(sRQName, sTrCode, '', sScrNo)
            if errorCode:
                self.logging('[Error] Code = {} in orderRefresh()'.format(errorCode))
            self.logging('Finished orderRefresh()')
        except Exception as error:
            self.logging('[Exception] {} in orderRefresh()'.format(error))
            error = '{}'.format(error)
            if error == 'CommRqData(): 조회과부하':
                self.logging('[재요청중...] in orderRefresh()')
                tr.Timer(0.25, self.orderRefresh).start()

    def holdingRefresh(self):
        # 보유중인 종목
        sRQName = '계좌정보조회'
        sTrCode = TrList.OPW['TR_OPW30003']
        sScrNo = self.sScrNo
        try:
            self.logging('Start holdingRefresh()')
            self.kiwoom.SetInputValue('계좌번호', self.sAccNo)
            self.kiwoom.SetInputValue('비밀번호', '')
            self.kiwoom.SetInputValue('비밀번호입력매체', '00')
            self.kiwoom.SetInputValue('통화코드', 'USD')
            errorCode = self.kiwoom.CommRqData(sRQName, sTrCode, '', sScrNo)
            if errorCode:
                self.logging('[Error] Code = {} in holdingRefresh()'.format(errorCode))
            self.logging('Finished holdingRefresh()')
        except Exception as error:
            self.logging('[Exception] {} in holdingRefresh()'.format(error))
            error = '{}'.format(error)
            if error == 'CommRqData(): 조회과부하':
                self.logging('[재요청중...] in holdingRefresh()')
                tr.Timer(0.25, self.holdingRefresh).start()

    def historyRefresh(self):
        # 거래완료 종목
        sRQName = '계좌정보조회'
        sTrCode = TrList.OPW['TR_OPW30007']
        sScrNo = self.sScrNo
        try:
            self.logging('Start historyRefresh()')
            self.kiwoom.SetInputValue('조회일자', time.strftime('%Y%m%d'))
            self.kiwoom.SetInputValue('계좌번호', self.sAccNo)
            self.kiwoom.SetInputValue('비밀번호', '')
            self.kiwoom.SetInputValue('비밀번호입력매체', '00')
            self.kiwoom.SetInputValue('통화코드', 'USD')
            self.kiwoom.SetInputValue('종목코드', '')
            errorCode = self.kiwoom.CommRqData(sRQName, sTrCode, '', sScrNo)
            if errorCode:
                self.logging('[Error] Code = {} in historyRefresh()'.format(errorCode))
            self.logging('Finished historyRefresh()')
        except Exception as error:
            self.logging('[Exception] {} in historyRefresh()'.format(error))
            error = '{}'.format(error)
            if error == 'CommRqData(): 조회과부하':
                self.logging('[재요청중...] in historyRefresh()')
                tr.Timer(0.25, self.historyRefresh).start()

    def jangoRefresh(self):
        # 미체결 종목
        sRQName = '계좌정보조회'
        sTrCode = TrList.OPW['TR_OPW30009']
        sScrNo = self.sScrNo
        try:
            self.logging('Start jangoRefresh()')
            self.kiwoom.SetInputValue('계좌번호', self.sAccNo)
            self.kiwoom.SetInputValue('비밀번호', '')
            self.kiwoom.SetInputValue('비밀번호입력매체', '00')
            # self.kiwoom.SetInputValue('통화코드', 'USD')
            errorCode = self.kiwoom.CommRqData(sRQName, sTrCode, '', sScrNo)
            if errorCode:
                self.logging('[Error] Code = {} in jangoRefresh()'.format(errorCode))
            self.logging('Finished jangoRefresh()')
        except Exception as error:
            self.logging('[Exception] {} in jangoRefresh()'.format(error))
            error = '{}'.format(error)
            if error == 'CommRqData(): 조회과부하':
                self.logging('[재요청중...] in jangoRefresh()')
                tr.Timer(0.25, self.jangoRefresh).start()

    def getExpireDate(self, fullCode):
        # 월물 만기일 조회
        strMaster = self.kiwoom.GetGlobalFutOpCodeInfoByCode(fullCode)
        expireDate = strMaster[150:158]

        return expireDate

    def getRemainDays(self, fullCode):
        # 월물 잔여일수 조회
        expireDate = self.getExpireDate(fullCode)

        now = datetime.datetime.now()
        past = datetime.datetime.strptime(expireDate, "%Y%m%d")
        diff = now - past

        return diff.days

    def getNextCode(self, code):
        # 다음 주문 종목코드 판별
        codeList = self.kiwoom.GetGlobalFutureCodelist(code).split(";")
        if len(codeList) < 2:
            return ""

        days = self.getRemainDays(codeList[0])

        nextCode = codeList[1] if days >= -3 else codeList[0]

        return nextCode

    def orderOpen(self, nOrderType, sCode, nQty, sPrice, sStop, sHogaGb):
        # nOrderType - 주문유형(1:신규매도, 2:신규매수, 3:매도취소, 4:매수취소, 5:매도정정, 6:매수정정)
        # sHogaGb - 거래구분(1:시장가, 2:지정가, 3:STOP, 4:STOP LIMIT)

        sRQName = '계좌정보조회'
        sScreenNo = self.sScrNo
        sAccNo = self.sAccNo

        try:
            self.logging('Start orderOpen()')
            errorCode = self.kiwoom.SendOrder(sRQName, sScreenNo, sAccNo, nOrderType, sCode, nQty, sPrice, sStop,
                                              sHogaGb, "")
            if errorCode:
                self.logging('■[Error] Code = {} in orderOpen()'.format(errorCode))
            self.logging('Finished orderOpen()')

        except Exception as error:
            self.logging('■[Exception] {} in orderOpen()'.format(error))

    def orderClose(self, nOrderType, sCode, nQty, sPrice, sStop, sHogaGb):
        sRQName = '계좌정보조회'
        sScreenNo = self.sScrNo
        sAccNo = self.sAccNo

        try:
            self.logging('Start orderClose()')
            errorCode = self.kiwoom.SendOrder(self, sRQName, sScreenNo, sAccNo, nOrderType, sCode, nQty, sPrice, sStop,
                                              sHogaGb, "")
            if errorCode:
                self.logging('■[Error] Code = {} in orderClose()'.format(errorCode))
            self.logging('Finished orderClose()')

        except Exception as error:
            self.logging('■[Exception] {} in orderClose()'.format(error))

    def orderCancel(self, nOrderType, sCode, nQty, sHogaGb, sOrgOrderNo):
        sRQName = '계좌정보조회'
        sScreenNo = self.sScrNo
        sAccNo = self.sAccNo

        try:
            self.logging('Start orderCancel()')
            errorCode = self.kiwoom.SendOrder(self, sRQName, sScreenNo, sAccNo, nOrderType, sCode, nQty, "0", "0",
                                              sHogaGb, sOrgOrderNo)
            if errorCode:
                self.logging('■[Error] Code = {} in orderCancel()'.format(errorCode))
            self.logging('Finished orderCancel()')

        except Exception as error:
            self.logging('■[Exception] {} in orderCancel()'.format(error))

    def orderModify(self, nOrderType, sCode, nQty, sPrice, sHogaGb, sOrgOrderNo):
        sRQName = '계좌정보조회'
        sScreenNo = self.sScrNo
        sAccNo = self.sAccNo

        try:
            self.logging('Start orderModify()')
            errorCode = self.kiwoom.SendOrder(self, sRQName, sScreenNo, sAccNo, nOrderType, sCode, nQty, sPrice, "0",
                                              sHogaGb, sOrgOrderNo)
            if errorCode:
                self.logging('■[Error] Code = {} in orderModify()'.format(errorCode))
            self.logging('Finished orderModify()')

        except Exception as error:
            self.logging('■[Exception] {} in orderModify()'.format(error))

    def retrieveChart(self, code):
        # 차트 조회
        sRQName = '계좌정보조회'
        sTrCode = TrList.OPC['TR_OPC10002']
        sScrNo = self.sScrNo
        try:
            self.logging('Start retrieveChart()')
            self.kiwoom.SetInputValue('종목코드', code)
            self.kiwoom.SetInputValue('시간단위', '15')
            errorCode = self.kiwoom.CommRqData(sRQName, sTrCode, '', sScrNo)
            if errorCode:
                self.logging('[Error] Code = {} in retrieveChart()'.format(errorCode))
            self.logging('Finished retrieveChart()')
        except Exception as error:
            self.logging('[Exception] {} in retrieveChart()'.format(error))
            # error = '{}'.format(error)
            # if error == 'CommRqData(): 조회과부하':
            #     self.logging('[재요청중...] in retrieveChart()')
            #     tr.Timer(2, self.retrieveChart).start()

    def applyTrade(self):
        self.logging('Start applyTrade()')
        result = self.db.select_trading_info(self.sAccNo)
        result.set_index("magic_no", inplace=True)

        for mtg_no in range(len(self.mtg)):
            mtg = self.mtg[mtg_no]

            df1 = self.df_order[self.df_order['종목코드'].str.contains(mtg.code)]
            df2 = self.df_holding[self.df_holding['종목코드'].str.contains(mtg.code)]

            df1 = df1.sum() if not df1.empty else pd.DataFrame()
            df2 = df2.sum() if not df2.empty else pd.DataFrame()

            if not df2.empty:
                tableItem = QTableWidgetItem(str(df2['평가손익']))
                tableItem.setForeground(QBrush(self.getPriceForm(df2['평가손익'])))
            else:
                tableItem = QTableWidgetItem("")

            tableItem.setTextAlignment(Qt.AlignRight)
            self.tbAlgorithm.setItem(mtg_no, 2, tableItem)

            if (not df1.empty and df1['매도수구분'] == 1) or (not df2.empty and df2['매도수구분'] == 1):
                tableItem = QTableWidgetItem("SELL")
            elif (not df1.empty and df1['매도수구분'] == 2) or (not df2.empty and df2['매도수구분'] == 2):
                tableItem = QTableWidgetItem("BUY")
            else:
                tableItem = QTableWidgetItem("READY")

            tableItem.setTextAlignment(Qt.AlignCenter)
            self.tbAlgorithm.setItem(mtg_no, 3, tableItem)

            # trading_info_status 보정
            status = result.loc[mtg.magic_no].fillna(0)

            if df2.empty and status.contract != 0:
                self.db.delete_trading_info_status(self.sAccNo, mtg.magic_no, mtg.releaseDate)
            elif not df2.empty and status.contract < df2['수량']:
                if status.contract == 0:
                    self.db.insert_trading_info_status(self.sAccNo, mtg.magic_no, df2['현재가격'], df2['수량'])
                else:
                    self.db.update_trading_info_status(self.sAccNo, mtg.magic_no, df2['현재가격'], df2['수량'])

        self.logging('Finished applyTrade()')

    def getOrderInfo(self, mtg):
        # 현재 상태 확인
        trade = MyTrade()

        result = self.db.select_trading_info_status(self.sAccNo, mtg.magic_no).iloc[0]

        df_holding = self.df_holding[self.df_holding['종목코드'].str.contains(mtg.code)]
        if len(df_holding) > 0:
            trade.orderType = mtg.OP_SELL if df_holding.iloc[0]['매도수구분']== 1 else mtg.OP_BUY
            trade.totalProfit = df_holding['평가손익'].sum()
            trade.startDate = result['start_date']
            trade.startPrice = result['start_price']
            trade.lastPrice = result['last_price']
            trade.degree = result['degree']
            trade.contract = int(df_holding.iloc[0]['수량'])
            trade.releaseTime = result['release_date']
            trade.price = df_holding.iloc[0]['현재가격']
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

            tableItem = QTableWidgetItem("CHECKING")
            tableItem.setTextAlignment(Qt.AlignCenter)
            self.tbAlgorithm.setItem(mtg_no, 3, tableItem)

            # 차트 조회
            self.df_cur = pd.DataFrame()
            self.retrieveChart(self.getNextCode(mtg.code))
            # self.tr_event_loop = QEventLoop()
            # QTimer.singleShot(1000, self.tr_event_loop.quit)
            # QTimer.singleShot(1000, self.tr_event_loop.exit)
            # self.tr_event_loop.exec_()

            if self.df_cur.empty:
                tableItem = QTableWidgetItem("NODATA")
                tableItem.setTextAlignment(Qt.AlignCenter)
                self.tbAlgorithm.setItem(mtg_no, 3, tableItem)
                continue

            # self.logging('>>> df_cur: ' + self.df_cur.index[-1])

            mtg.df_cur = self.df_cur

            signal = mtg.checkForOpen()
            # if mtg.code == 'MSF':
            #     signal = mtg.OP_BUY

            if signal == mtg.OP_SELL:
                tableItem = QTableWidgetItem("SELL")
            elif signal == mtg.OP_BUY:
                tableItem = QTableWidgetItem("BUY")
            else:
                tableItem = QTableWidgetItem("READY")
            tableItem.setTextAlignment(Qt.AlignCenter)
            self.tbAlgorithm.setItem(mtg_no, 3, tableItem)

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

        # 포지션 청산 체크
        for mtg_no in range(len(self.mtg)):
            mtg = self.mtg[mtg_no]

            status = self.tbAlgorithm.item(mtg_no, 3)
            if status.text() != "BUY" and status.text() != "SELL":
                continue

            # tableItem = QTableWidgetItem("CHECKING")
            # tableItem.setTextAlignment(Qt.AlignCenter)
            # self.tbAlgorithm.setItem(mtg_no, 3, tableItem)

            self.getOrderInfo(mtg)
            if mtg.trade is None:
                continue

            tableItem = QTableWidgetItem(str(mtg.trade.startDate) if mtg.trade.contract > 0 else '')
            tableItem.setTextAlignment(Qt.AlignCenter)
            self.tbAlgorithm.setItem(mtg_no, 4, tableItem)

            tableItem = QTableWidgetItem(str(mtg.trade.startPrice) if mtg.trade.contract > 0 else '')
            tableItem.setTextAlignment(Qt.AlignCenter)
            self.tbAlgorithm.setItem(mtg_no, 5, tableItem)

            tableItem = QTableWidgetItem(str(mtg.trade.lastPrice) if mtg.trade.contract > 0 else '')
            tableItem.setTextAlignment(Qt.AlignCenter)
            self.tbAlgorithm.setItem(mtg_no, 6, tableItem)

            tableItem = QTableWidgetItem(str(int(mtg.trade.degree)) if mtg.trade.contract > 0 else '')
            tableItem.setTextAlignment(Qt.AlignCenter)
            self.tbAlgorithm.setItem(mtg_no, 7, tableItem)

            tableItem = QTableWidgetItem(str(int(mtg.trade.contract)) if mtg.trade.contract > 0 else '')
            tableItem.setTextAlignment(Qt.AlignCenter)
            self.tbAlgorithm.setItem(mtg_no, 8, tableItem)

            if mtg.trade.totalProfit < 0:
                # 차트 조회
                self.df_cur = pd.DataFrame()
                self.retrieveChart(self.getNextCode(mtg.code))

                if self.df_cur.empty:
                    tableItem = QTableWidgetItem("NODATA")
                    tableItem.setTextAlignment(Qt.AlignCenter)
                    self.tbAlgorithm.setItem(mtg_no, 3, tableItem)
                    continue

                mtg.df_cur = self.df_cur
                mtg.close = self.df_cur.iloc[-1]['Close']
            else:
                df_holding = self.df_holding[self.df_holding['종목코드'].str.contains(mtg.code)]
                mtg.close = df_holding.iloc[0]['현재가격']

            signal = mtg.checkForClose()

            # if signal == mtg.OP_SELL:
            #     tableItem = QTableWidgetItem("SELL")
            # elif signal == mtg.OP_BUY:
            #     tableItem = QTableWidgetItem("BUY")
            # else:
            #     tableItem = QTableWidgetItem("READY")

            # tableItem.setTextAlignment(Qt.AlignCenter)
            # self.tbAlgorithm.setItem(mtg_no, 3, tableItem)

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
                    self.logging(f'■ 추가 주문: 매도, #{mtg.magic_no}, {sCode}, {lots}')
                    self.orderOpen(1, sCode, lots, "0", "0", "1")  # 시장가 매도
                elif signal == mtg.OP_BUY:
                    sCode = self.getNextCode(mtg.code)
                    lots = mtg.getNextOrderLots()
                    self.logging(f'■ 추가 주문: 매수, #{mtg.magic_no}, {sCode}, {lots}')
                    self.orderOpen(2, sCode, lots, "0", "0", "1")  # 시장가 매수

        self.logging('Finished closeCheck()')

    ###########################################################################
    # 이벤트 수신부
    # 이벤트 발생시 데이터 처리
    # #########################################################################

    # 요청 이벤트 수신부
    def ReceiveTrData(self, sScrNo, sRQName, sTrCode, sRecordName, sPrevNext):
        # self.logging("[Event] OnReceiveTrData")
        # self.logging("sScrNo : {}".format(sScrNo))
        # self.logging("sRQName : {}".format(sRQName))
        # self.logging("sTrCode : {}".format(sTrCode))
        # self.logging("sRecordName : {}".format(sRecordName))
        # self.logging("sPrevNext : {}".format(sPrevNext))

        if sRQName == '종목정보조회':
            if sTrCode == TrList.OPT['TR_OPT10001']:
                try:
                    sCode = sPrevNext.split(' ')[0][2:8]
                    nIndex = self.dicItemInfo[sCode]
                    for singleData in self.itemInfo[nIndex].singleData:
                        sValue = self.kiwoom.GetCommData(sTrCode, sRQName, 0, singleData[0]).strip()
                        self.itemInfo[nIndex].SetSingleData(singleData[0], sValue)  # 종목별 SingleData 입력
                        # self.logging("{} : {}".format(singleData[0], self.itemInfo[nIndex].GetSingleData(singleData[0])))
                except Exception as error:
                    self.logging("[Exception][종목정보조회] {} in ReceiveTrData ".format(error))

        elif sRQName == '계좌정보조회':
            if sTrCode == TrList.OPW['TR_OPW30001']:
                try:
                    self.df_order, fldList = self.kiwoom.GetCommDataToPandas(sTrCode, sRQName)

                    df = self.df_order.copy()
                    df['매도수구분'] = df['매도수구분'].replace({1: '매도', 2: '매수'})

                    self.tbOrder.setRowCount(df.shape[0])
                    self.tbOrder.setColumnCount(df.shape[1])
                    self.tbOrder.setHorizontalHeaderLabels(df.columns)

                    for i in range(df.shape[0]):
                        for j in range(df.shape[1]):
                            org = df.iloc[i, j]

                            if isinstance(org, int) or isinstance(org, float) or np.issubdtype(type(org), np.integer):
                                if not str(df.columns[j]).endswith("주문번호"):
                                    tableItem = QTableWidgetItem(str('{:,}'.format(org)))
                                else:
                                    tableItem = QTableWidgetItem(str(org))
                                # tableItem.setTextAlignment(Qt.AlignCenter)
                            else:
                                tableItem = QTableWidgetItem(str(org))

                            tableItem.setTextAlignment(Qt.AlignCenter)
                            self.tbOrder.setItem(i, j, tableItem)

                    self.tbOrder.show()

                except Exception as error:
                    self.logging("[Exception][계좌정보조회] {} in ReceiveTrData ".format(error))

            if sTrCode == TrList.OPW['TR_OPW30003']:
                try:
                    self.df_holding, fldList = self.kiwoom.GetCommDataToPandas(sTrCode, sRQName)

                    df = self.df_holding.copy()
                    df['매도수구분'] = df['매도수구분'].replace({1: '매도', 2: '매수'})
                    df = df.rename(columns={"평가손익": "평가손익($)", "약정금액": "약정금액($)", "평가금액": "평가금액($)",
                                            "수익율": "수익율(%)", "수수료": "수수료($)"})

                    self.tbHolding.setRowCount(df.shape[0])
                    self.tbHolding.setColumnCount(df.shape[1])
                    self.tbHolding.setHorizontalHeaderLabels(df.columns)

                    for i in range(df.shape[0]):
                        for j in range(df.shape[1]):
                            org = df.iloc[i, j]
                            fld = fldList[j]

                            if isinstance(org, int) or isinstance(org, float) or np.issubdtype(type(org), np.integer):
                                tableItem = QTableWidgetItem(str('{:,}'.format(org)))
                                # tableItem.setTextAlignment(Qt.AlignCenter)
                            else:
                                tableItem = QTableWidgetItem(str(org))

                            tableItem.setTextAlignment(Qt.AlignCenter)
                            if fld.__contains__("color") and fld["color"] == "Y":
                                tableItem.setForeground(QBrush(self.getPriceForm(org)))
                            self.tbHolding.setItem(i, j, tableItem)

                    self.tbHolding.show()
                    # self.applyTrade()

                except Exception as error:
                    self.logging("[Exception][계좌정보조회] {} in ReceiveTrData ".format(error))

            if sTrCode == TrList.OPW['TR_OPW30007']:
                try:
                    self.df_history, fldList = self.kiwoom.GetCommDataToPandas(sTrCode, sRQName)

                    df = self.df_history.copy()
                    df['매도수구분'] = df['매도수구분'].replace({1: '매도', 2: '매수'})
                    df = df.rename(columns={"청산손익": "청산손익($)", "수수료": "수수료($)", "순손익": "순손익($)"})

                    self.tbHistory.setRowCount(df.shape[0])
                    self.tbHistory.setColumnCount(df.shape[1])
                    self.tbHistory.setHorizontalHeaderLabels(df.columns)

                    for i in range(df.shape[0]):
                        for j in range(df.shape[1]):
                            org = df.iloc[i, j]
                            fld = fldList[j]

                            if isinstance(org, int) or isinstance(org, float) or np.issubdtype(type(org), np.integer):
                                tableItem = QTableWidgetItem(str('{:,}'.format(org)))
                                # tableItem.setTextAlignment(Qt.AlignCenter)
                            else:
                                tableItem = QTableWidgetItem(str(org))

                            tableItem.setTextAlignment(Qt.AlignCenter)
                            if fld.__contains__("color") and fld["color"] == "Y":
                                tableItem.setForeground(QBrush(self.getPriceForm(org)))
                            self.tbHistory.setItem(i, j, tableItem)

                    self.df_history["주문번호"] = self.df_history['체결시간'].str.replace("/", "").str.replace(":", "").str.replace(" ", "")
                    self.df_history["주문번호"] = self.df_history["주문번호"] + self.df_history.index.astype('str').to_list()

                    self.tbHistory.show()

                except Exception as error:
                    self.logging("[Exception][계좌정보조회] {} in ReceiveTrData ".format(error))

            if sTrCode == TrList.OPW['TR_OPW30009']:
                try:
                    self.df_summary, fldList = self.kiwoom.GetCommDataToPandas(sTrCode, sRQName, True)
                    if len(self.df_summary) > 0:
                        tableItem = QTableWidgetItem(str('{:,}'.format(self.df_summary.iloc[0]['외화예수금'])))
                        tableItem.setTextAlignment(Qt.AlignCenter)
                        self.tbAccount.setItem(0, 0, tableItem)

                        tableItem = QTableWidgetItem(str('{:,}'.format(self.df_summary.iloc[0]['선물청산손익'])))
                        tableItem.setTextAlignment(Qt.AlignCenter)
                        tableItem.setForeground(QBrush(self.getPriceForm(self.df_summary.iloc[0]['선물청산손익'])))
                        self.tbAccount.setItem(0, 1, tableItem)

                        tableItem = QTableWidgetItem(str('{:,}'.format(self.df_summary.iloc[0]['예탁자산평가'])))
                        tableItem.setTextAlignment(Qt.AlignCenter)
                        self.tbAccount.setItem(0, 2, tableItem)

                        tableItem = QTableWidgetItem(str('{:,}'.format(self.df_summary.iloc[0]['선물평가손익'])))
                        tableItem.setTextAlignment(Qt.AlignCenter)
                        tableItem.setForeground(QBrush(self.getPriceForm(self.df_summary.iloc[0]['선물평가손익'])))
                        self.tbAccount.setItem(0, 3, tableItem)

                        tableItem = QTableWidgetItem(str('{:,}'.format(self.df_summary.iloc[0]['포지션증거금'])))
                        tableItem.setTextAlignment(Qt.AlignCenter)
                        self.tbAccount.setItem(0, 4, tableItem)

                    self.tbAccount.show()

                except Exception as error:
                    self.logging("[Exception][계좌정보조회] {} in ReceiveTrData ".format(error))

            if sTrCode == TrList.OPC['TR_OPC10002']:
                try:
                    self.df_cur, _ = self.kiwoom.GetCommDataToPandas(sTrCode, sRQName)
                    self.df_cur = self.df_cur[['체결시간', '시가', '고가', '저가', '현재가']].copy()
                    self.df_cur.columns = ['Time', 'Open', 'High', 'Low', 'Close']
                    self.df_cur.set_index('Time', inplace=True)
                    self.df_cur.sort_index(ascending=True, inplace=True)

                except Exception as error:
                    self.logging("[Exception][계좌정보조회] {} in ReceiveTrData ".format(error))

                # if self.tr_event_loop is not None:
                #     self.tr_event_loop.exit()

    # 실시간 이벤트 수신부
    def ReceiveRealData(self, sCode, sRealType, sRealData):
        # self.logging("[Event] ReceiveRealData")
        # self.logging("sCode : {}".format(sCode))
        # self.logging("sRealType : {}".format(sRealType))
        # self.logging("sRealData : {}".format(sRealData))
        if sRealType == "해외옵션호가" or sRealType == "해외선물호가":
            try:
                nIndex = self.dicItemInfo[sCode]
                for realFid in self.itemInfo[nIndex].dicRealHoga.keys():
                    sValue = self.kiwoom.GetCommRealData(sRealType, realFid).strip()
                    self.itemInfo[nIndex].SetRealHoga(realFid, sValue)
                    # self.logging("[{0}] : {1}".format(realFid, self.itemInfo[nIndex].GetRealHoga(realFid))) # 입력 확인
                # self.SetTbAcountItem(nIndex)
            except Exception as error:
                self.logging("[해외옵션선물호가][Exception] {} in ReceiveRealData".format(error))
        elif sRealType == "해외옵션시세" or sRealType == "해외선물시세":
            try:
                nIndex = self.dicItemInfo[sCode]
                for realFid in self.itemInfo[nIndex].dicRealMarketPrice.keys():
                    sValue = self.kiwoom.GetCommRealData(sRealType, realFid).strip()
                    self.itemInfo[nIndex].SetRealMarketPrice(realFid, sValue)
                    # self.logging("[{0}] : {1}".format(realFid, self.itemInfo[nIndex].GetRealMarketPrice(realFid))) # 입력 확인
                # nIndex = self.accountInfo.dicMyItems[sCode]
                # self.accountInfo.myItemInfo[nIndex].SetCurrentPrice()
                nIndex = self.dicItemInfo[sCode]
                self.SetTbAcountItem(nIndex)
            except Exception as error:
                self.logging("[해외옵션선물시세][Exception] {} in ReceiveRealData".format(error))
        elif sRealType == "마진콜" or sRealType == "잔고" or sRealType == "주문체결":
            self.logging('[RealData] {} '.format(sRealType))

    def ReceiveMsg(self, sScrNo, sRQname, sTrCode, sMsg):
        # self.logging('[ReceiveMsg]sScrNo : {}'.format(sScrNo))
        # self.logging('[ReceiveMsg]sRQname : {}'.format(sRQname))
        self.logging('[ReceiveMsg]sTrCode : {}'.format(sTrCode))
        self.logging('[ReceiveMsg]sMsg : {}'.format(sMsg))
        # self.login_event_loop.exit()

    def ReceiveChejanData(self, sGubun, nItemCnt, sFidList):
        # self.logging('[ReceiveChejanData]sGubun : {}'.format(sGubun))
        # self.logging('[ReceiveChejanData]nItemCnt : {}'.format(nItemCnt))
        # self.logging('[ReceiveChejanData]sFidList : {}'.format(sFidList))

        try:
            # fids = sFidList.split(';')
            self.logging('sGubun : {}'.format(sGubun))
            if sGubun == '0':  # 해외선물옵션주문
                # self.chejanReceive[0] += 1
                self.orderRefresh()
                # tr.Timer(0.3, self._SetOrderInfo).start()
            elif sGubun == '1':  # 해외선물옵션체결
                # self.chejanReceive[1] += 1
                # tr.Timer(0.3, self._SetAccountInfo).start()
                self.jangoRefresh()
                self.orderRefresh()
                self.holdingRefresh()
                self.historyRefresh()
            # if tr.active_count() == 1:
            #     tr.Timer(0.24, self._TrRequest).start()
        except Exception as error:
            self.logging("[Exception] {} in ReceiveChejanData ".format(error))

    # def _TrRequest(self):
    #     if self.chejanReceive[0] > 0:
    #         self._SetOrderInfo()
    #     if self.chejanReceive[1] > 0:
    #         self._SetAccountInfo()
    #     self.chejanReceive = [0, 0]

    def EventConnect(self, nErrCode):
        # 서버와 연결되거나 해제되었을 경우 발생되는 이벤트 처리 메소드
        try:
            # nErrCode(0 : 접속, 음수값 : 오류)
            if nErrCode == ErrorCode.OP_ERR_NONE:
                self.logging('Successed login')
                self.logging('Loading login information')
                # self.accountInfo.SetConnectState(True)
                # self.accountInfo.SetLoginInfo()
                # for i in range(len(self.accountInfo.loginInfo.accNo)-1):
                # self.cbAccountNum.addItem(self.accountInfo.loginInfo.accNo[i])
                # print(self.accountInfo.loginInfo.accNo[i])
                # self._InitItemInfo(True)
                self.logging('Completed Login!')

                self.timer.start()
            else:
                try:
                    # self.accountInfo.SetConnectState(False)
                    self._InitItemInfo(False)
                    msg = ErrorCode.CAUSE[nErrCode]
                except KeyError as error:
                    self.logging('[Error]' + str(error) + ' in EventConnect')
                finally:
                    print(msg)

        except Exception as error:
            self.logging('[Error]' + str(error) + ' in EventConnect')

        finally:
            try:
                self.loginEventLoop.exit()
            except AttributeError:
                pass

    def getPriceForm(self, sValue):
        if isinstance(sValue, int) or isinstance(sValue, float) or np.issubdtype(type(sValue), np.integer):
            if sValue < 0:
                return Qt.blue
            elif sValue > 0:
                return Qt.red

        return Qt.black

    # def setOrderIndex(self):
    #     for i in range(len(self.orderIndex)):
    #         self.orderIndex[i].clear()
    #     for key in self.accountInfo.orderInfo.keys():
    #         code = self.accountInfo.GetOrderInfo(key, '종목코드')
    #         nIndex = self.dicItemInfo[code]
    #         self.orderIndex[nIndex].append(key)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle(QStyleFactory.create('fusion'))

    myWindow = TraderMain()
    myWindow.show()

    app.exec_()

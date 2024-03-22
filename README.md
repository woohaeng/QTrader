# Q-Trader
- 키움증권 API 연동
- 해외선물 CME

## Qt Designer
- cmd> designer

## Environment
- 키움API는 Win32 에서만 실행가능

## Install package
- conda install -c conda-forge ta-lib (https://wolfzone.tistory.com/54)
- pip install pykiwoom
- pip install pymysql
- pip install pyqtwebengine
- pip install pyautogui
- pip install pyarrow
- pip install fastparquet
- pip install pandas==2.0.3

## Experiment
[ ADX : 20 ]
- SIGNAL      = 9613
- ADX         = 6158 ( 64.06 %)
- RSI         = 2519 ( 26.2 %)
- LONG TREND  = 5677 ( 59.06 %)
- SHORT TREND = 5268 ( 54.8 %)
- PASS        = 257 ( 2.67 %)

[ ADX : 15 ]
- SIGNAL      = 9613
- ADX         = 3232 ( 33.62 %)
- RSI         = 2519 ( 26.2 %)
- LONG TREND  = 5677 ( 59.06 %)
- SHORT TREND = 5268 ( 54.8 %)
- PASS        = 501 ( 5.21 %)

[ ADX : 15, RSI : 40, 60 ]
- SIGNAL      = 9613
- ADX         = 3232 ( 33.62 %)
- RSI         = 232 ( 2.41 %)
- LONG TREND  = 5677 ( 59.06 %)
- SHORT TREND = 5268 ( 54.8 %)
- PASS        = 1080 ( 11.23 %)
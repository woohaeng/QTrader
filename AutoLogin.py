import sys
import time
import ctypes
import pyautogui
import threading as tr


class AutoLogin:
    def __init__(self, user_pass, account_pass) :
        self.user_pass = user_pass
        self.account_pass = account_pass
        self.repeat_count = 0
        self.user_login = False
        self.account_login = False

    def run(self):
        self.enter_user_password()

    def enter_user_password(self):
        if not self.user_login:
            hwnd = ctypes.windll.user32.FindWindowW(None, "영웅문W Login")
            if hwnd == 0:
                self.repeat_count += 1
                if self.repeat_count < 180:
                    tr.Timer(1, self.enter_user_password).start()
                return

            time.sleep(1)
            pyautogui.moveTo(1335, 685)
            pyautogui.click()
            # time.sleep(0.1)
            pyautogui.write(self.user_pass)
            pyautogui.press('enter')

            self.user_login = True
            self.repeat_count = 0
            self.enter_account_password()

    def enter_account_password(self):
        if not self.account_login:
            hwnd = ctypes.windll.user32.FindWindowW(None, "계좌번호관리")
            if hwnd == 0:
                self.repeat_count += 1
                if self.repeat_count < 180:
                    tr.Timer(1, self.enter_account_password).start()
                return

            time.sleep(0.1)
            pyautogui.moveTo(1250, 650)
            pyautogui.click()
            # time.sleep(0.1)
            pyautogui.write(self.account_pass)
            pyautogui.press('enter')
            time.sleep(0.1)

            ctypes.windll.user32.PostMessageA(hwnd, 0x0010, 0, 0)

            self.account_login = True


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("비밀번호를 입력해 주세요.")
        exit(0)

    user_pass, account_pass = sys.argv[1], sys.argv[2]
    auto = AutoLogin(user_pass, account_pass)
    auto.run()

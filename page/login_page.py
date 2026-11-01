# -*- coding: utf-8 -*-
"""登录页 PO（路由 /user/login，定位均来自 2026-10-27 页面实测）"""
import time
from typing import Tuple

from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait

from page.base_page import BasePage

Locator = Tuple[str, str]


class LoginPage(BasePage):
    URL = "/user/login"

    I_USERNAME: Locator = (By.XPATH, "//input[@placeholder='请输入用户名']")
    I_PASSWORD: Locator = (By.XPATH, "//input[@placeholder='请输入密码']")
    BTN_LOGIN: Locator = (By.XPATH, "//button[normalize-space()='登 录']")
    CHK_REMEMBER: Locator = (By.XPATH, "//input[@type='checkbox']")
    LK_REGISTER: Locator = (By.XPATH, "//a[normalize-space()='注册租户']")

    # 首页特征：登录成功跳转 /dashboard/analysis 且欢迎语出现
    WELCOME = (By.XPATH, "//*[contains(normalize-space(),'欢迎您，')]")

    def login(self, username: str, password: str) -> None:
        """标准登录操作（页面级，真实用户路径）"""
        self.fill(self.I_USERNAME, username)
        self.fill(self.I_PASSWORD, password)
        self.click(self.BTN_LOGIN)

    def wait_login_success(self, timeout: int = 10) -> bool:
        """登录成功判定：URL 进入 dashboard"""
        try:
            WebDriverWait(self.driver, timeout).until(
                lambda d: "/dashboard/" in d.current_url)
            return True
        except Exception:  # noqa: BLE001 - 超时即视为未成功
            return False

    def validation_errors(self) -> list:
        """必填校验提示（antd 表单 explain 文案）。

        实测：退出后重进登录页时 explain 节点先插入 DOM 再播放显示动画，
        需轮询等待可见；取 textContent 规避渲染中的空 text。
        """
        errs = []
        deadline = time.time() + 5
        while time.time() < deadline:
            els = self.driver.find_elements(By.CSS_SELECTOR, ".ant-form-explain")
            errs = [e.get_attribute("textContent").strip() for e in els
                    if e.is_displayed() and e.get_attribute("textContent").strip()]
            if errs:
                return errs
            time.sleep(0.3)
        return errs

    def error_toast(self) -> str:
        """登录失败提示（message/notification）"""
        toast = self.message_text()
        if toast:
            return toast
        return self.text_of((By.CSS_SELECTOR, ".ant-notification-notice-message"))

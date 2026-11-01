# -*- coding: utf-8 -*-
"""关键字层：Excel 步骤表的反射分发执行器（计划 §3.1 Keywords 层职责）。

Excel 步骤格式（data/ui_cases.xlsx 关键字步骤列，分号分隔）：
    打开|/user/login;输入|请输入用户名|jsh;点击|登 录
关键字（与 keywords.xlsx 对应）：
    打开/登录/退出/输入/点击/选择/等待/断言URL/断言文本/断言行/断言消息
"""
import time

from selenium.webdriver.common.by import By

from page.bill_page import BillPage
from page.crud_page import CustomerPage, DepotPage, VendorPage
from page.login_page import LoginPage
from page.material_page import MaterialPage
from page.menu_frame import MenuFrame
from page.stock_report_page import StockReportPage
from utils.logger import get_logger

log = get_logger(__name__)


class KeywordExecutor:
    """把 Excel 关键字步骤分发到 PO 方法；页面通过路由字典定位"""

    def __init__(self, driver, base_url: str, admin_account: dict):
        self.driver = driver
        self.base_url = base_url.rstrip("/")
        self.admin = admin_account
        self.login_page = LoginPage(driver)
        self.menu = MenuFrame(driver)
        self._pages = {}  # 惰性实例化缓存

    # 页面注册表：路由后缀 → PO 工厂
    PAGE_FACTORIES = {
        "/user/login": lambda d: LoginPage(d),
        "/material/material": lambda d: MaterialPage(d),
        "/system/vendor": lambda d: VendorPage(d),
        "/system/customer": lambda d: CustomerPage(d),
        "/system/depot": lambda d: DepotPage(d),
        "/bill/purchase_order": lambda d: BillPage(d, "/bill/purchase_order", "供应商", "本次付款"),
        "/bill/purchase_in": lambda d: BillPage(d, "/bill/purchase_in", "供应商", "本次付款"),
        "/bill/purchase_back": lambda d: BillPage(d, "/bill/purchase_back", "供应商", "本次付款"),
        "/bill/sale_order": lambda d: BillPage(d, "/bill/sale_order", "客户", "本次收款"),
        "/bill/sale_out": lambda d: BillPage(d, "/bill/sale_out", "客户", "本次收款"),
        "/bill/sale_back": lambda d: BillPage(d, "/bill/sale_back", "客户", "本次收款"),
        "/bill/retail_out": lambda d: BillPage(d, "/bill/retail_out", "会员卡号", "收款金额"),
        "/bill/allocation_out": lambda d: BillPage(d, "/bill/allocation_out", "客户", "本次收款"),
        "/report/material_stock": lambda d: StockReportPage(d),
    }

    def page(self, path: str):
        po = self._pages.get(path)
        if po is None:
            factory = self.PAGE_FACTORIES[path]
            po = factory(self.driver)
            self._pages[path] = po
        return po

    # ---- 关键字实现（kw, *args）----
    def kw_打开(self, path: str):
        po = self.page(path).open(path)
        # 已登录会话打开登录页会被弹回首页：先退出再进（UI-AUTH-002/003 前置）
        if path == "/user/login" and self.menu.is_present(self.menu.LOGOUT, timeout=2):
            self.menu.logout()
            po = self.page(path).open(path)
        return po

    def kw_登录(self, username: str = "", password: str = ""):
        u = username or self.admin["login_name"]
        p = password or self.admin["password"]
        self.login_page.open()
        # 已登录会话打开登录页会被弹回首页，需先退出
        if self.menu.is_present(self.menu.LOGOUT, timeout=2):
            self.menu.logout()
            self.login_page.open()
        self.login_page.login(u, p)
        assert self.login_page.wait_login_success(), "登录未跳转首页"
        self.login_page.dismiss_popups()

    def kw_退出(self):
        self.menu.logout()

    def kw_输入(self, placeholder: str, text: str, path: str = None):
        page = self.page(path) if path else self.menu
        page.fill((By.XPATH, f"//input[@placeholder='{placeholder}']"), text)

    def kw_点击(self, text: str):
        self.menu.click((By.XPATH,
                         f"//button[contains(normalize-space(),'{text}')]"
                         f" | //a[contains(normalize-space(),'{text}')]"))

    def kw_等待(self, seconds: str):
        time.sleep(float(seconds))

    def kw_断言URL(self, expected: str):
        assert expected in self.driver.current_url, \
            f"URL 断言失败: {self.driver.current_url} 不含 {expected}"

    def kw_断言文本(self, text: str):
        assert self.menu.is_present((By.XPATH, f"//*[contains(normalize-space(),'{text}')]")), \
            f"页面未出现文本: {text}"

    def kw_断言消息(self, text: str):
        msg = self.menu.message_text()
        assert text in msg, f"提示文案断言失败: 期望含'{text}', 实际'{msg}'"

    def kw_断言行(self, path: str, row_text: str):
        page = self.page(path)
        row = page.find_row(row_text)
        assert row, f"列表未找到行: {row_text}"

    def kw_截图(self, name: str):
        self.menu.screenshot(name)

    # ---- 分发 ----
    def run_step(self, step: str) -> None:
        step = step.strip()
        if not step:
            return
        parts = step.split("|")
        kw = "kw_" + parts[0].strip()
        args = [p.strip() for p in parts[1:]]
        fn = getattr(self, kw, None)
        assert fn, f"未知关键字: {parts[0]}（步骤: {step}）"
        log.info("执行关键字步骤: %s", step)
        fn(*args)

    def run_case(self, steps: str) -> None:
        for step in steps.split(";"):
            self.run_step(step)

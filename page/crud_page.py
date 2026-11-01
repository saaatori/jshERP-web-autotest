# -*- coding: utf-8 -*-
"""基础资料通用 CRUD 页 PO：供应商/客户/仓库/会员/结算账户共用同构列表+弹窗模式。

字段定位以 2026-10-27 实测弹窗 placeholder 为准；查询输入框各页 placeholder
未逐一走查，采用"查询区首个文本输入框"通用定位，执行时按实际断言修正。
"""
import time
from typing import Tuple

from selenium.webdriver.common.by import By

from page.base_page import BasePage

Locator = Tuple[str, str]


class CrudPage(BasePage):
    # 查询区：各列表页首个文本输入框（查询区结构同构，实测）
    BTN_QUERY: Locator = (By.XPATH, "//button[normalize-space()='查 询']")

    # 弹窗按钮（基础资料弹窗为 取 消/保 存，实测）
    M_BTN_SAVE: Locator = (By.XPATH, "//div[contains(@class,'ant-modal')][last()]"
                                     "//button[normalize-space()='保 存']")
    M_BTN_CANCEL: Locator = (By.XPATH, "//div[contains(@class,'ant-modal')][last()]"
                                       "//button[normalize-space()='取 消']")

    def __init__(self, driver, url: str, field_placeholders: dict):
        super().__init__(driver)
        self.URL = url
        self.fields = {}
        for label, ph in field_placeholders.items():
            self.fields[label] = (By.XPATH,
                                  f"//div[contains(@class,'ant-modal')][last()]"
                                  f"//input[@placeholder='{ph}']")

    def query_input(self) -> Locator:
        """查询区首个文本输入框（排除弹窗内的输入框，避免命中残留隐藏弹窗表单）"""
        return (By.XPATH, "(//input[@type='text' and not(@placeholder='')"
                          " and not(ancestor::div[contains(@class,'ant-modal')])])[1]")

    def query(self, keyword: str) -> None:
        self.fill(self.query_input(), keyword)
        self.click(self.BTN_QUERY)
        time.sleep(1.2)

    def create(self, data: dict) -> None:
        """新增记录：data 为 {字段名: 值}，字段名须在 field_placeholders 内"""
        self.click(self.toolbar_button("新增"))
        time.sleep(1)
        for label, value in data.items():
            self.fill(self.fields[label], value)
        self.click(self.M_BTN_SAVE)
        time.sleep(1.5)
        self.confirm_dialog()

    def create_expect_error(self, data: dict) -> str:
        """重复创建等异常场景：保存被拒，返回提示文案（UI-BAS-002/UI-GOODS-002 同构）"""
        self.click(self.toolbar_button("新增"))
        time.sleep(1)
        for label, value in data.items():
            self.fill(self.fields[label], value)
        self.click(self.M_BTN_SAVE)
        time.sleep(1.2)
        msg = self.message_text() or self.text_of(
            (By.CSS_SELECTOR, ".ant-modal .ant-form-explain"))
        self.click(self.M_BTN_CANCEL)
        return msg

    def row(self, name: str) -> dict | None:
        return self.find_row(name)


class VendorPage(CrudPage):
    """供应商信息 /system/vendor（弹窗字段实测）"""

    def __init__(self, driver):
        super().__init__(driver, "/system/vendor", {
            "名称": "请输入名称",
            "联系人": "请输入联系人",
            "手机号码": "请输入手机号码",
            "联系电话": "请输入联系电话",
            "电子邮箱": "请输入电子邮箱",
            "期初应付": "请输入期初应付",
            "税率": "请输入税率",
            "地址": "请输入地址",
        })


class CustomerPage(CrudPage):
    """客户信息 /system/customer（与供应商同构）"""

    def __init__(self, driver):
        super().__init__(driver, "/system/customer", {
            "名称": "请输入名称",
            "联系人": "请输入联系人",
            "手机号码": "请输入手机号码",
            "联系电话": "请输入联系电话",
            "电子邮箱": "请输入电子邮箱",
            "期初应收": "请输入期初应收",
            "税率": "请输入税率",
            "地址": "请输入地址",
        })


class DepotPage(CrudPage):
    """仓库信息 /system/depot（弹窗字段实测）"""

    def __init__(self, driver):
        super().__init__(driver, "/system/depot", {
            "仓库名称": "请输入仓库名称",
            "仓库地址": "请输入仓库地址",
            "仓储费": "请输入仓储费",
            "搬运费": "请输入搬运费",
            "排序": "请输入排序",
        })


class AccountPage(CrudPage):
    """结算账户 /system/account"""

    def __init__(self, driver):
        super().__init__(driver, "/system/account", {
            "名称": "请输入名称",
            "编号": "请输入编号",
            "期初金额": "请输入期初金额",
            "备注": "请输入备注",
            "排序": "请输入排序",
        })

# -*- coding: utf-8 -*-
"""商品信息页 PO（/material/material；定位来自 2026-10-27 实测弹窗与列表结构）"""
import time
from typing import Tuple

from selenium.webdriver.common.by import By

from page.base_page import BasePage

Locator = Tuple[str, str]


class MaterialPage(BasePage):
    URL = "/material/material"

    # 查询区
    I_KEYWORD: Locator = (By.XPATH, "//input[@placeholder='请输入条码、名称、助记码等查询']")
    BTN_QUERY: Locator = (By.XPATH, "//button[normalize-space()='查 询']")

    # 新增弹窗：双页签（基本信息 / 库存数量 / 图片信息，实测）
    M_TAB_STOCK: Locator = (By.XPATH, "//div[contains(@class,'ant-modal')][last()]"
                                      "//div[@role='tab'][normalize-space()='库存数量']")
    M_LABELS = {
        "名称": (By.XPATH, "//div[contains(@class,'ant-modal')][last()]"
                          "//input[@placeholder='请输入名称']"),
        "单位": (By.XPATH, "//div[contains(@class,'ant-modal')][last()]"
                          "//input[@placeholder='输入单位']"),
        "条码": (By.XPATH, "//div[contains(@class,'ant-modal')][last()]"
                          "//input[@placeholder='请输入条码']"),
        "采购价": (By.XPATH, "//div[contains(@class,'ant-modal')][last()]"
                            "//input[@placeholder='请输入采购价']"),
        "零售价": (By.XPATH, "//div[contains(@class,'ant-modal')][last()]"
                            "//input[@placeholder='请输入零售价']"),
        "销售价": (By.XPATH, "//div[contains(@class,'ant-modal')][last()]"
                            "//input[@placeholder='请输入销售价']"),
        "最低售价": (By.XPATH, "//div[contains(@class,'ant-modal')][last()]"
                              "//input[@placeholder='请输入最低售价']"),
        "期初库存": (By.XPATH, "//div[contains(@class,'ant-modal')][last()]"
                              "//input[@placeholder='请输入期初库存数量']"),
    }
    M_BTN_SAVE: Locator = (By.XPATH, "//div[contains(@class,'ant-modal')][last()]"
                                     "//button[contains(.,'保存')]")
    M_BTN_CANCEL: Locator = (By.XPATH, "//div[contains(@class,'ant-modal')][last()]"
                                       "//button[normalize-space()='取 消']")

    # ---- 查询 ----
    def query(self, keyword: str) -> None:
        self.fill(self.I_KEYWORD, keyword)
        self.click(self.BTN_QUERY)
        time.sleep(1.2)  # 列表刷新

    def row_by_name(self, name: str) -> dict | None:
        return self.find_row(name)

    # ---- 新增（UI-GOODS-001；结构：基本信息 + 库存数量两页签）----
    def open_create_modal(self) -> None:
        self.click(self.toolbar_button("新增"))
        time.sleep(1)
        self.dismiss_popups()  # intro.js 引导可能指向弹窗字段，拦截点击

    def create(self, name: str, unit: str = "个", barcode: str = "",
               purchase: str = "10", sale: str = "20", low: str = "20",
               initial_stock: str = "0") -> None:
        self.open_create_modal()
        self.fill(self.M_LABELS["名称"], name)
        self.fill(self.M_LABELS["单位"], unit)
        # 切换到库存数量页签填写条码与价格（实测双页签结构）
        self.click(self.M_TAB_STOCK)
        time.sleep(0.5)
        if barcode:
            self.fill(self.M_LABELS["条码"], barcode)
        self.fill(self.M_LABELS["采购价"], purchase)
        self.fill(self.M_LABELS["零售价"], sale)
        self.fill(self.M_LABELS["销售价"], sale)
        self.fill(self.M_LABELS["最低售价"], low)
        self.fill(self.M_LABELS["期初库存"], initial_stock)
        self.click(self.M_BTN_SAVE)
        time.sleep(1.5)

    def create_expect_error(self, data: dict) -> str:
        """异常保存场景：填写后保存，返回提示文案（可能为空——见 UI-GOODS-002 实测）"""
        self.open_create_modal()
        self.click(self.M_TAB_STOCK)  # 条码在库存数量页签，先切换
        time.sleep(0.5)
        for label, value in data.items():
            self.fill(self.M_LABELS[label], value)
        self.click(self.M_BTN_SAVE)
        time.sleep(1.2)
        msg = self.message_text() or self.text_of(
            (By.CSS_SELECTOR, ".ant-modal .ant-form-explain"))
        if self.is_present(self.M_BTN_CANCEL, timeout=2):
            self.click(self.M_BTN_CANCEL)  # 被拦截时弹窗仍在，取消退出
        time.sleep(0.8)
        return msg

    def save_expect_validation(self) -> list:
        """名称留空直接保存，取必填校验提示（UI-GOODS-003）"""
        self.open_create_modal()
        self.click(self.M_BTN_SAVE)
        time.sleep(0.8)
        els = self.find_all((By.CSS_SELECTOR, ".ant-modal .ant-form-explain"))
        errs = [e.get_attribute("textContent").strip() for e in els
                if e.get_attribute("textContent").strip()]
        self.click(self.M_BTN_CANCEL)
        return errs

    # ---- 启用/停用（UI-GOODS-004）----
    def set_enabled(self, name: str, enable: bool) -> None:
        self.query(name)
        self.check_row(name)
        self.click(self.toolbar_button("启用" if enable else "禁用"))
        self.confirm_dialog()
        time.sleep(1.2)

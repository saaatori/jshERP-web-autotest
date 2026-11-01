# -*- coding: utf-8 -*-
"""商品库存报表页 PO（/report/material_stock，实测列：库存详情/条码/名称/…/库存/库存金额）"""
import time
from typing import Tuple

from selenium.webdriver.common.by import By

from page.base_page import BasePage

Locator = Tuple[str, str]


class StockReportPage(BasePage):
    URL = "/report/material_stock"

    I_KEYWORD: Locator = (By.XPATH, "//input[@placeholder='请输入条码、名称、助记码、规格、型号等信息']")
    BTN_QUERY: Locator = (By.XPATH, "//button[normalize-space()='查 询']")

    def query(self, keyword: str) -> None:
        self.fill(self.I_KEYWORD, keyword)
        self.click(self.BTN_QUERY)
        time.sleep(1.2)

    def stock_of(self, name_or_barcode: str) -> dict | None:
        """按条码/名称取报表行（含 库存/库存金额/单位 列）"""
        return self.find_row(name_or_barcode)

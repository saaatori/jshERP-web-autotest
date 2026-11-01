# -*- coding: utf-8 -*-
"""单据列表通用页 PO：采购订单/采购入库/销售订单/销售出库/零售/调拨/退货共用
"查询区 + 工具栏 + 双表 + 编辑弹窗" 模式（2026-10-27 实测结构）。

弹窗内定位约定（实测快照顺序）：
- 组织(供应商/客户)下拉 = 弹窗内第 1 个 antd select
- 结算账户下拉 = 弹窗内最后一个 antd select（底部）
- 明细行第 1 行：仓库下拉 = 行内第 1 个 select，条码下拉 = 行内第 2 个 select
- 数量 = 行 td[8] 输入框，单价 = 行 td[9] 输入框（列序 #/仓库/条码/名称/规格/库存/单位/数量/单价/金额/税率/税额/价税合计/备注）
"""
import time
from typing import Tuple

from selenium.webdriver.common.by import By

from page.base_page import BasePage

Locator = Tuple[str, str]


class BillPage(BasePage):
    # 查询区（实测：单据编号/商品信息/单据日期）
    I_NUMBER: Locator = (By.XPATH, "//input[@placeholder='请输入单据编号']")
    BTN_QUERY: Locator = (By.XPATH, "//button[normalize-space()='查 询']")

    # 编辑弹窗
    M_BTN_SAVE: Locator = (By.XPATH, "//div[@data-ui-active-modal='1']"
                                     "//button[contains(normalize-space(),'保存')"
                                     " and not(contains(.,'审核'))]")
    M_BTN_SAVE_AUDIT: Locator = (By.XPATH, "//div[@data-ui-active-modal='1']"
                                           "//button[normalize-space()='保存并审核']")
    M_BTN_CANCEL: Locator = (By.XPATH, "//div[@data-ui-active-modal='1']"
                                       "//button[normalize-space()='取 消']")

    def __init__(self, driver, url: str, organ_label: str = "供应商",
                 pay_label: str = "本次付款"):
        super().__init__(driver)
        self.URL = url
        self.organ_label = organ_label   # 供应商 / 客户 / 会员卡号
        self.pay_label = pay_label       # 本次付款 / 本次收款 / 收款金额

    # ---- 弹窗内定位 ----
    def mark_modal(self) -> None:
        """给当前可见的业务弹窗打标记；antd 关闭后 DOM 残留（实测），
        [last()] 会命中隐藏弹窗，故显式标记 offsetParent 非空的弹窗。"""
        self.driver.execute_script(
            """
            document.querySelectorAll('[data-ui-active-modal]')
              .forEach(m => m.removeAttribute('data-ui-active-modal'));
            const vis = [...document.querySelectorAll('.ant-modal')]
              .filter(m => m.offsetParent !== null);
            if (vis.length) vis[vis.length - 1].setAttribute('data-ui-active-modal', '1');
            """)

    def _modal(self) -> Locator:
        self.mark_modal()
        return (By.XPATH, "//div[@data-ui-active-modal='1']")

    def _modal_select(self, index: int) -> Locator:
        """弹窗内第 index 个 antd select 根节点（1 起；排除 __clear 等隐藏子元素）"""
        return (By.XPATH, f"(//div[@data-ui-active-modal='1']"
                          f"//div[contains(concat(' ',normalize-space(@class),' '),' ant-select-selection ')]"
                          f")[{index}]")

    def _modal_select_by_label(self, label: str) -> Locator:
        """按字段标签定位其后第一个下拉（结算账户等）"""
        return (By.XPATH, f"//div[@data-ui-active-modal='1']"
                          f"//*[contains(normalize-space(),'{label}')]"
                          f"/following::div[contains(concat(' ',normalize-space(@class),' '),' ant-select-selection ')][1]")

    def _modal_input_by_label(self, label: str) -> Locator:
        return (By.XPATH, f"//div[@data-ui-active-modal='1']"
                          f"//*[contains(normalize-space(),'{label}')]"
                          f"/following::input[1]")

    def _modal_input_by_placeholder(self, ph: str) -> Locator:
        return (By.XPATH, f"//div[@data-ui-active-modal='1']"
                          f"//input[@placeholder='{ph}']")

    def _mark_detail_row(self, row_index: int = 1, header: str = "数量") -> int:
        """标记明细网格第 row_index 数据行并返回目标列序。

        实测：明细网格经 portal 渲染在 .ant-modal 之外的 document 层级（全文档
        仅 2 个 tr：表头 + 数据行），故在全文档范围找表头行；每次重算以对抗
        Vue 重渲染。"""
        idx = self.driver.execute_script(
            """
            document.querySelectorAll('[data-ui-active-row]')
              .forEach(r => r.removeAttribute('data-ui-active-row'));
            const vis = [...document.querySelectorAll('.ant-modal')]
              .filter(m => m.offsetParent !== null);
            if (!vis.length) return 0;
            const modal = vis[vis.length - 1];
            modal.setAttribute('data-ui-active-modal', '1');
            // 明细网格为 <div class="tr"><div class="td"> 自定义结构（实测，非原生 tr）
            const rows = [...modal.querySelectorAll('.tr')].filter(
              t => t.getClientRects().length);
            const headerRow = rows.find(r => {
              const ts = [...r.children].map(c => c.textContent.trim());
              return ts.includes('条码') && (ts.includes('数量') || ts.includes('单价'));
            });
            if (!headerRow) return 0;
            const cells = [...headerRow.children];
            // 精确匹配优先（'数量' 不得命中 '原数量'），退回包含匹配
            let col = cells.findIndex(c => c.textContent.trim() === arguments[0]);
            if (col < 0) col = cells.findIndex(c => c.textContent.trim().includes(arguments[0]));
            col = col + 1;
            const dataRows = rows.filter(r =>
              r !== headerRow && r.querySelector('input, .ant-select'));
            const row = dataRows[arguments[1] - 1];
            if (row) row.setAttribute('data-ui-active-row', '1');
            return col;
            """, header, row_index)
        return int(idx or 0)

    def _detail_row(self, row_index: int = 1) -> Locator:
        self._mark_detail_row(row_index)
        return (By.XPATH, "//div[@data-ui-active-row='1']")

    def _detail_input(self, header: str, row_index: int = 1) -> Locator:
        col = self._mark_detail_row(row_index, header)
        return (By.XPATH, f"//div[@data-ui-active-row='1']/*[{col}]//input")

    def _detail_select(self, header: str, row_index: int = 1) -> Locator:
        col = self._mark_detail_row(row_index, header)
        return (By.XPATH, f"//div[@data-ui-active-row='1']/*[{col}]"
                          f"//div[contains(concat(' ',normalize-space(@class),' '),' ant-select-selection ')]")

    # ---- 列表操作 ----
    def query_by_number(self, number: str, widen_date: bool = True) -> None:
        """按单据编号查询。实测订单列表页默认日期区间的结束边界会漏掉当日单据
        （API 建单后 UI 查不到），故默认主动写入近7天~明天的日期区间。"""
        from datetime import datetime, timedelta
        self.fill(self.I_NUMBER, number)
        if widen_date:
            start = (By.XPATH, "//input[@placeholder='开始时间']")
            end = (By.XPATH, "//input[@placeholder='结束时间']")
            today = datetime.now()
            self._fill_date(start, (today - timedelta(days=7)).strftime("%Y-%m-%d"))
            self._fill_date(end, (today + timedelta(days=1)).strftime("%Y-%m-%d"))
        self.click(self.BTN_QUERY)
        time.sleep(1.2)

    def _fill_date(self, locator: Locator, value: str) -> None:
        """antd 日期输入（input 带 readonly，实测需先移除）：输入后回车提交"""
        el = self.find(locator)
        self.driver.execute_script("arguments[0].removeAttribute('readonly');"
                                   "arguments[0].value='';", el)
        el.send_keys(value)
        el.send_keys(u"\ue007")  # ENTER
        time.sleep(0.3)

    def find_bill(self, number: str) -> dict | None:
        """按单据编号查行，返回列名→文本（金额列断言用）"""
        return self.find_row(number)

    def status_of(self, number: str) -> str:
        row = self.find_bill(number)
        return (row or {}).get("状态", "")

    def open_new_modal(self) -> None:
        self.click(self.toolbar_button("新增"))
        self.wait.until(lambda d: self._visible_modal_count(d) > 0)
        time.sleep(0.8)
        self.dismiss_popups()  # intro.js 引导可能指向弹窗字段，拦截点击
        self.mark_modal()

    @staticmethod
    def _visible_modal_count(d) -> int:
        return d.execute_script(
            "return [...document.querySelectorAll('.ant-modal')]"
            ".filter(m => m.offsetParent !== null).length")

    def select_barcode(self, row_index: int, barcode: str) -> None:
        """明细行条码选择：条码列为可搜索 ant-select（antd v3 形态，聚焦后搜索框
        才可见），复用 search_select 点击展开 → 输入 → 选项点选。"""
        self.search_select(self._detail_select("条码", row_index), barcode)
        time.sleep(0.5)  # 等待行联动刷新（带出名称/单位/库存）

    # ---- 弹窗填写（新增采购入库/销售出库等）----
    def fill_modal(self, organ: str, items: list, account: str = None,
                   pay: str = None) -> dict:
        """items: [(条码, 数量, 单价), ...]；返回单据编号。组织下拉为可搜索 select。"""
        self.open_new_modal()
        self.search_select(self._modal_select(1), organ)
        time.sleep(0.5)
        for i, (barcode, qty, price) in enumerate(items, start=1):
            if i > 1:  # 追加行
                self.click((By.XPATH, "//div[@data-ui-active-modal='1']"
                                      "//button[contains(.,'插入行')]"))
                time.sleep(0.5)
            self.select_barcode(i, barcode)
            self.fill(self._detail_input("数量", i), qty)
            self.fill(self._detail_input("单价", i), price)
        if account:
            self.search_select(self._modal_select_by_label("结算账户"), account)
        if pay is not None:
            pay_ph = "请输入本次付款" if "付款" in self.pay_label else "请输入本次收款"
            self.fill(self._modal_input_by_placeholder(pay_ph), pay)
        return {"number": self._read_bill_number()}

    def _read_bill_number(self) -> str:
        el = self.find((By.XPATH, "//div[@data-ui-active-modal='1']"
                                  "//input[@placeholder='请输入单据编号']"))
        return el.get_attribute("value") or ""

    def save(self, expect_close: bool = True) -> None:
        self.mark_modal()
        self.click(self.M_BTN_SAVE)
        time.sleep(1.5)
        self.confirm_dialog()  # 可能弹出确认
        if expect_close:
            # antd 关闭后 DOM 仍在（实测残留 display:none 弹窗），判不可见
            num_input = (By.XPATH, "//div[@data-ui-active-modal='1']"
                                   "//input[@placeholder='请输入单据编号']")
            self.wait.until(lambda d: not any(
                el.is_displayed() for el in d.find_elements(*num_input)))
        time.sleep(1)

    def cancel_modal(self) -> None:
        self.click(self.M_BTN_CANCEL)

    # ---- 状态迁移操作（审核/反审核/转单，均需先勾选行）----
    def _select_bill(self, number: str) -> None:
        self.query_by_number(number)
        row = self.find_bill(number)
        assert row, f"列表中未找到单据 {number}"
        self.check_row(number)

    def audit(self, number: str, expect_status: str = "已审核") -> None:
        self._select_bill(number)
        self.click(self.toolbar_button("审核"))
        self.confirm_dialog()
        time.sleep(1.5)
        self.wait.until(lambda d: self.status_of(number) == expect_status)

    def unaudit(self, number: str) -> None:
        self._select_bill(number)
        self.click(self.toolbar_button("反审核"))
        self.confirm_dialog()
        time.sleep(1.5)

    def transfer(self, number: str, target_button: str, items: list = None,
                 pay: str = None) -> str:
        """勾选源单 → 转采购入库/转销售出库/转采购退货 → 弹窗预填 → 保存；返回新单号。
        勾选后按钮刚生效，首次 JS 点击可能被吞（实测），轮询等编辑器出现并重试。"""
        self._select_bill(number)
        num_input = (By.XPATH, "//div[@data-ui-active-modal='1']"
                               "//input[@placeholder='请输入单据编号']")
        before = self._visible_modal_count(self.driver)
        self.click(self.toolbar_button(target_button))
        deadline = time.time() + 10
        opened = False
        while time.time() < deadline:
            time.sleep(0.8)
            self.confirm_dialog()
            self.mark_modal()
            if self._visible_modal_count(self.driver) > before and \
                    self.is_present(num_input, 1):
                opened = True
                break
            self.click(self.toolbar_button(target_button))
        assert opened, f"点击 {target_button} 后编辑器未打开"
        time.sleep(0.5)
        if items:  # 部分执行场景：改数量
            for i, (qty,) in enumerate(items, start=1):
                self.fill(self._detail_input("数量", i), qty)
        if pay is not None:
            pay_ph = "请输入本次付款" if "付款" in self.pay_label else "请输入本次收款"
            self.fill(self._modal_input_by_placeholder(pay_ph), pay)
        new_number = self._read_bill_number()
        self.save()
        return new_number

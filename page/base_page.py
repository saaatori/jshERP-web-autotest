# -*- coding: utf-8 -*-
"""BasePage：显式等待、点击/输入、AntD 组件封装、失败截图（计划 §3.3 稳定性策略）"""
import os
import time
from typing import List, Optional, Tuple

from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from selenium.webdriver import Chrome
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from utils.config import load_config, project_root
from utils.logger import get_logger

log = get_logger(__name__)

Locator = Tuple[str, str]

# AntD 通用结构
ANTD_MESSAGE = (By.CSS_SELECTOR, ".ant-message .ant-message-notice:last-child")
ANTD_MODAL_CLOSE = (By.CSS_SELECTOR, ".ant-modal .ant-modal-close")
ANTD_NOTIFICATION_CLOSE = (By.CSS_SELECTOR, ".ant-notification-notice-close")
ANTD_CONFIRM_OK = (By.CSS_SELECTOR, ".ant-modal-confirm-btns .ant-btn-primary")
ANTD_POPUP = (By.CSS_SELECTOR, ".ant-modal:not([style*='display: none']), "
                             ".ant-notification-notice, .ant-modal-confirm")
BODY_ROWS = (By.XPATH, "(//div[contains(@class,'ant-table-wrapper')]"
                       "//table)[last()]//tbody/tr")


class BasePage:
    URL = ""

    def __init__(self, driver: Chrome):
        self.driver = driver
        self.cfg = load_config()
        self.base_url = self.cfg["base_url"].rstrip("/")
        self.timeout = int(self.cfg.get("explicit_wait", 15))
        self.wait = WebDriverWait(driver, self.timeout)

    # ---- 导航 ----
    def open(self, path: Optional[str] = None) -> "BasePage":
        url = self.base_url + (path or self.URL)
        log.info("打开页面 %s", url)
        self.driver.get(url)
        self.wait_for_ready()
        self.dismiss_popups()
        return self

    def wait_for_ready(self, timeout: int = 15) -> None:
        WebDriverWait(self.driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete")

    def current_url(self) -> str:
        return self.driver.current_url

    # ---- 等待与查找 ----
    def find(self, locator: Locator):
        return self.wait.until(EC.visibility_of_element_located(locator))

    def find_all(self, locator: Locator) -> List:
        try:
            self.wait.until(EC.presence_of_all_elements_located(locator))
        except TimeoutException:
            return []
        return self.driver.find_elements(*locator)

    def find_clickable(self, locator: Locator):
        return self.wait.until(EC.element_to_be_clickable(locator))

    # ---- 基础操作 ----
    def click(self, locator: Locator) -> None:
        """标准点击，动画页/遮挡时降级 JS 点击（登录页背景动画实测需要）"""
        try:
            self.find_clickable(locator).click()
        except (ElementClickInterceptedException, TimeoutException,
                WebDriverException) as e:
            log.warning("标准点击失败(%s)，降级 JS 点击 %s", type(e).__name__, locator)
            el = self.wait.until(EC.presence_of_element_located(locator))
            self.driver.execute_script("arguments[0].click();", el)

    def fill(self, locator: Locator, text: str) -> None:
        """输入：优先真实键盘事件；元素存在但 is_displayed 误判时（antd 页签动画
        面板实测）降级原生 setter + input/change 事件，保证 v-model 同步。"""
        try:
            el = self.find(locator)
            el.clear()
            el.send_keys(str(text))
        except TimeoutException:
            el = self.wait.until(EC.presence_of_element_located(locator))
            self.driver.execute_script(
                "const el=arguments[0], v=arguments[1];"
                "const proto = el.tagName==='TEXTAREA' ? HTMLTextAreaElement.prototype"
                " : HTMLInputElement.prototype;"
                "Object.getOwnPropertyDescriptor(proto,'value').set.call(el,v);"
                "el.dispatchEvent(new Event('input',{bubbles:true}));"
                "el.dispatchEvent(new Event('change',{bubbles:true}));",
                el, str(text))

    def text_of(self, locator: Locator) -> str:
        try:
            return self.find(locator).text.strip()
        except TimeoutException:
            return ""

    def is_present(self, locator: Locator, timeout: int = 3) -> bool:
        try:
            WebDriverWait(self.driver, timeout).until(
                EC.presence_of_element_located(locator))
            return True
        except TimeoutException:
            return False

    # ---- AntD 组件封装 ----
    def dismiss_popups(self) -> None:
        """关闭浮层：欢迎通知、首页新手引导弹窗（含'上一步/下一步'特征）、intro.js 提示。

        严禁关闭业务弹窗：引导弹窗仅按'上一步'按钮特征识别。
        """
        # 1. 通知关闭钮
        for i in range(3):
            els = self.driver.find_elements(*ANTD_NOTIFICATION_CLOSE)
            if not els:
                break
            for el in els:
                try:
                    self.driver.execute_script("arguments[0].click();", el)
                except StaleElementReferenceException:
                    pass
            time.sleep(0.4)
        # 2. 引导弹窗（特征：含"上一步"步骤按钮的 ant-modal）
        guide = (By.XPATH, "//div[contains(@class,'ant-modal')][.//button"
                           "[contains(normalize-space(),'上一步')]]"
                           "//button[contains(@class,'ant-modal-close')]")
        for i in range(3):
            els = self.driver.find_elements(*guide)
            if not els:
                break
            for el in els:
                try:
                    self.driver.execute_script("arguments[0].click();", el)
                except StaleElementReferenceException:
                    pass
            time.sleep(0.4)
        # 3. intro.js 引导：点跳过/完成按钮结束（不移除节点，避免干扰 Vue 渲染）
        for attempt in range(3):
            btns = self.driver.find_elements(
                By.CSS_SELECTOR, ".introjs-skipbutton, .introjs-donebutton")
            if not btns:
                break
            for btn in btns:
                try:
                    self.driver.execute_script("arguments[0].click();", btn)
                except StaleElementReferenceException:
                    pass
            time.sleep(0.4)
        log.debug("浮层清理完成")

    def confirm_dialog(self) -> bool:
        """若存在 antd 确认框则点击确定（审核/删除等操作可能触发）"""
        if self.is_present(ANTD_CONFIRM_OK, timeout=2):
            self.click(ANTD_CONFIRM_OK)
            time.sleep(0.5)
            return True
        return False

    def message_text(self) -> str:
        """读取 antd message 提示文案（保存成功/失败提示）"""
        try:
            el = WebDriverWait(self.driver, 3).until(
                EC.visibility_of_element_located(ANTD_MESSAGE))
            return el.text.strip()
        except TimeoutException:
            return ""

    def _open_select(self, combobox: Locator) -> None:
        """点击 select 外层容器展开下拉（内层 selection span 点击实测不触发展开）。
        普通输入框（无 ant-select 祖先，如订单编辑器条码列）则点击输入框本身。"""
        if hasattr(self, "mark_modal"):
            self.mark_modal()  # 单据弹窗：重打标记（Vue 重渲染会清除旧标记）
        el = self.find(combobox)
        containers = el.find_elements(
            By.XPATH, "./ancestor::div[contains(@class,'ant-select')][1]")
        target = containers[0] if containers else el
        self.driver.execute_script("arguments[0].click();", target)
        self.wait.until(lambda d: any(
            x.is_displayed() and "hidden" not in (x.get_attribute("class") or "")
            for x in d.find_elements(By.CSS_SELECTOR, ".ant-select-dropdown")))
        time.sleep(0.3)

    def _click_dropdown_option(self, text: str, exact: bool) -> bool:
        """在可见 dropdown 中按文本点选选项（JS 过滤，类名兼容 antd v3/v4）。
        返回是否点中；不可见 dropdown 一律忽略。"""
        script = """
          const kw = arguments[0], exact = arguments[1];
          const dds = [...document.querySelectorAll('.ant-select-dropdown')]
            .filter(d => d.offsetHeight > 0 &&
                   !d.className.includes('ant-select-dropdown-hidden'));
          for (const dd of dds) {
            const lis = [...dd.querySelectorAll('li')].filter(li =>
              (li.className.includes('ant-select-item-option') ||
               li.className.includes('ant-select-dropdown-menu-item')));
            const hit = lis.find(li => {
              const t = li.textContent.trim();
              return exact ? t === kw : t.includes(kw);
            });
            if (hit) { hit.click(); return true; }
          }
          return false;
        """
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            if self.driver.execute_script(script, text, exact):
                time.sleep(0.5)
                return True
            time.sleep(0.4)
        return False

    def select_option(self, combobox: Locator, option_text: str) -> None:
        """antd 下拉选择：展开 → 选项列表中按文本点选"""
        self._open_select(combobox)
        assert self._click_dropdown_option(option_text, exact=True), \
            f"下拉选项未找到: {option_text}"

    def search_select(self, combobox: Locator, keyword: str) -> None:
        """下拉选择（可搜索）：展开 → 轮询等待搜索框可见后输入 → 点选匹配项。
        antd v3 的 search__field 聚焦后才可见（条码列实测），需轮询。"""
        self._open_select(combobox)
        field = None
        deadline = time.time() + 5
        while time.time() < deadline:
            # 只取当前展开 select 的搜索框（其它下拉的残留搜索框同为可见，实测踩坑）
            fields = [f for f in self.driver.find_elements(
                          By.CSS_SELECTOR,
                          ".ant-select-open .ant-select-search__field, "
                          ".ant-select-open input.ant-select-search__field")
                      if f.is_displayed()]
            if fields:
                field = fields[0]
                break
            time.sleep(0.3)
        if field is not None:
            field.clear()
            field.send_keys(keyword)
        time.sleep(0.8)  # 远程搜索选项渲染
        assert self._click_dropdown_option(keyword, exact=False), \
            f"下拉选项未找到: {keyword}"

    # ---- 表格封装（固定表头双 table 模式，实测结构）----
    def headers(self) -> List[str]:
        head = (By.XPATH, "(//div[contains(@class,'ant-table-wrapper')]"
                          "//table)[last()]/preceding::table[.//th][1]//th")
        cells = self.find_all(head) or self.find_all(
            (By.CSS_SELECTOR, ".ant-table-thead th"))
        return [c.text.strip() for c in cells]

    def rows(self) -> List[List[str]]:
        cells = []
        for tr in self.find_all(BODY_ROWS):
            tds = tr.find_elements(By.TAG_NAME, "td")
            cells.append([td.text.strip() for td in tds])
        return cells

    def find_row(self, row_text: str) -> Optional[dict]:
        """按行内唯一文本定位行，返回 列名→单元格文本 字典（计划 §3.4：不依赖行序）"""
        heads = self.headers()
        for cells in self.rows():
            if row_text in cells:
                data = dict(zip(heads, cells))
                return data
        return None

    def check_row(self, row_text: str) -> None:
        """勾选行内复选框：与 find_row 用同一 BODY_ROWS 定位（固定列克隆表
        会导致含文本 tr 定位命中错误表格，实测踩坑），找到后 JS 勾选。"""
        rows = self.find_all(BODY_ROWS)
        for tr in rows:
            cells = [td.text.strip() for td in tr.find_elements(By.TAG_NAME, "td")]
            if row_text in cells:
                cb = tr.find_element(By.XPATH, ".//input[@type='checkbox']")
                if not cb.is_selected():
                    self.driver.execute_script("arguments[0].click();", cb)
                time.sleep(0.3)
                return
        raise AssertionError(f"未找到可勾选的行: {row_text}")

    def toolbar_button(self, name: str) -> Locator:
        return (By.XPATH, f"//button[.//span[normalize-space()='{name}']]")

    # ---- 截图（失败取证，计划 §3.3 第4条）----
    def screenshot(self, name: str) -> str:
        shots = os.path.join(project_root(), "reports", "screenshots")
        os.makedirs(shots, exist_ok=True)
        path = os.path.join(shots, f"{name}_{int(time.time() * 1000)}.png")
        try:
            self.driver.save_screenshot(path)
            log.info("已保存截图 %s", path)
        except WebDriverException as e:
            log.error("截图失败: %s", e)
        return path

    def save_page_source(self, name: str) -> str:
        shots = os.path.join(project_root(), "reports", "pages")
        os.makedirs(shots, exist_ok=True)
        path = os.path.join(shots, f"{name}_{int(time.time() * 1000)}.html")
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.driver.page_source)
        return path

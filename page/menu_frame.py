# -*- coding: utf-8 -*-
"""主框架 PO：侧边菜单、多页签、顶栏、退出登录（全局组件，路由无关）"""
import time
from typing import Tuple

from selenium.common.exceptions import TimeoutException
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from page.base_page import BasePage

Locator = Tuple[str, str]


class MenuFrame(BasePage):
    MENU_ITEMS = (By.XPATH, "//aside//li[contains(@class,'ant-menu-submenu') or contains(@class,'ant-menu-item')]")
    MENU_LINKS = (By.XPATH, "//aside//a[@href]")
    TABS = (By.XPATH, "//div[contains(@class,'ant-tabs')]//div[@role='tab']")
    LOGOUT = (By.XPATH, "//a[.//text()[contains(.,'退出登录')]]")

    def menu_texts(self) -> list:
        """一级菜单文案列表（UI-SYS-001：10 个一级模块；首页为无子级 menu-item）"""
        els = self.find_all((By.XPATH, "//aside//li[contains(@class,'ant-menu-submenu') or contains(@class,'ant-menu-item')]"))
        texts = []
        for el in els:
            t = el.text.strip().splitlines()
            if t:
                texts.append(t[-1].strip())  # 最后一行为菜单名（首行可能是图标别名）
        return texts

    def open_menu(self, module: str, page: str = None, route: str = None) -> None:
        """进入功能页：悬停+点击展开一级菜单 → 点子菜单链接 → 校验路由。

        实测：侧边菜单为 antd inline 模式（需点击展开）；子菜单链接的标准
        点击偶发被拦截，采用 JS 点击；引导弹窗遮挡时先清理再重试一次。
        """
        item = (By.XPATH, f"//aside//li[contains(@class,'ant-menu-submenu')"
                          f" and .//span[normalize-space()='{module}']]"
                          f"//div[contains(@class,'ant-menu-submenu-title')]")
        el = self.wait.until(EC.visibility_of_element_located(item))
        ActionChains(self.driver).move_to_element(el).perform()
        if page:
            link = (By.XPATH, f"//aside//li[contains(@class,'ant-menu-item')]"
                              f"//a[.//span[normalize-space()='{page}']]")
            try:
                self.click(item)  # 展开 inline 子菜单
                link_el = WebDriverWait(self.driver, 5).until(
                    EC.visibility_of_element_located(link))
                self.driver.execute_script("arguments[0].click();", link_el)
                if route:
                    WebDriverWait(self.driver, 8).until(
                        lambda d: route in d.current_url)
            except TimeoutException:
                # 引导弹窗等浮层遮挡场景：清理后重试一次
                self.dismiss_popups()
                self.click(item)
                link_el = self.wait.until(EC.visibility_of_element_located(link))
                self.driver.execute_script("arguments[0].click();", link_el)
                if route:
                    WebDriverWait(self.driver, 8).until(
                        lambda d: route in d.current_url)
        time.sleep(0.8)  # 路由切换渲染

    def tab_titles(self) -> list:
        """当前打开的 SPA 页签标题（UI-SYS-002 多页签）"""
        return [e.text.strip().replace("close", "").strip()
                for e in self.find_all(self.TABS)]

    def close_tab(self, title: str) -> None:
        tab = (By.XPATH, f"//div[@role='tab'][contains(.,'{title}')]"
                         f"//*[contains(@class,'anticon-close')]")
        self.click(tab)
        time.sleep(0.8)

    def welcome_text(self) -> str:
        el = self.find_all((By.XPATH, "//*[contains(normalize-space(),'欢迎您，')]"))
        return el[0].text.strip() if el else ""

    def logout(self) -> None:
        """右上角退出登录（UI-AUTH-004；实测入口为右上角链接）"""
        self.click(self.LOGOUT)
        self.confirm_dialog()
        time.sleep(1.5)

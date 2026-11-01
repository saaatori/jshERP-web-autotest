# -*- coding: utf-8 -*-
"""Chrome Driver 工厂：版本由 Selenium Manager 自动匹配（Chrome 156，附录C 锁定策略）"""
from selenium import webdriver

from utils.logger import get_logger

log = get_logger(__name__)


def create_driver(cfg: dict) -> webdriver.Chrome:
    opts = webdriver.ChromeOptions()
    if cfg.get("headless"):
        opts.add_argument("--headless=new")
    w, h = str(cfg.get("window_size", "1920x1080")).split("x")
    opts.add_argument(f"--window-size={w},{h}")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-infobars")
    opts.add_argument("--no-sandbox")
    opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    opts.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(options=opts)
    driver.implicitly_wait(cfg.get("implicit_wait", 0))
    log.info("Chrome 已启动, window=%s, headless=%s", cfg.get("window_size"), cfg.get("headless"))
    return driver

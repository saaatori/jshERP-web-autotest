# -*- coding: utf-8 -*-
"""统一 logging：控制台 + 滚动文件（logs/ui_autotest.log）"""
import logging
import os
from logging.handlers import RotatingFileHandler

from utils.config import project_root

_FMT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
_configured = False


def _setup() -> None:
    global _configured
    if _configured:
        return
    log_dir = os.path.join(project_root(), "logs")
    os.makedirs(log_dir, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    fmt = logging.Formatter(_FMT)
    sh = logging.StreamHandler()
    sh.setFormatter(fmt)
    root.addHandler(sh)
    fh = RotatingFileHandler(
        os.path.join(log_dir, "ui_autotest.log"),
        maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8",
    )
    fh.setFormatter(fmt)
    root.addHandler(fh)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    _setup()
    return logging.getLogger(name)

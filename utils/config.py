# -*- coding: utf-8 -*-
"""配置加载：config/ui_config.yaml 单例；支持环境变量覆盖（Jenkins 用）"""
import os

import yaml

_CFG = None


def load_config() -> dict:
    global _CFG
    if _CFG is None:
        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "config", "ui_config.yaml",
        )
        with open(path, encoding="utf-8") as f:
            _CFG = yaml.safe_load(f)
        # Jenkins/CI 用环境变量覆盖无头模式
        if os.environ.get("HEADLESS"):
            _CFG["headless"] = os.environ["HEADLESS"].lower() == "true"
    return _CFG


def project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

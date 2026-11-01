# -*- coding: utf-8 -*-
"""手动兜底清理：按 UITEST 前缀扫删测试残留数据。

用法：.venv/Scripts/python.exe utils/sweep_now.py
（通常不需要手动跑——conftest 的会话兜底钩子每轮测试结束会自动执行同样逻辑）
"""
import sys

sys.path.insert(0, ".")

from utils.api_helper import JshApi
from utils.config import load_config


def main():
    cfg = load_config()
    acct = cfg["account"]["api"]
    api = JshApi(cfg["api_base_url"], acct["login_name"], acct["password"])
    api.login()
    removed = api.sweep_test_data()
    print("清理结果:", removed)


if __name__ == "__main__":
    main()

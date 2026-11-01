# -*- coding: utf-8 -*-
"""Excel 驱动入口（计划 §3.1 Testcases 层）：解析 data/ui_cases.xlsx 并分发执行。

执行方式两类：
- keyword  ：关键字步骤由 keywords/executor.py 反射执行
- codecase ：复杂链路场景由 pytest 代码用例承载，本驱动登记跳过（Excel 为追溯源）
"""
import allure
import pytest

from keywords.executor import KeywordExecutor
from utils.config import load_config
from utils.excel_util import read_sheet

pytestmark = [pytest.mark.usefixtures("admin_logged")]

DATA = None


def load_cases():
    global DATA
    if DATA is None:
        import os
        from utils.config import project_root
        path = os.path.join(project_root(), "data", "ui_cases.xlsx")
        DATA = read_sheet(path, sheet="ui_cases", header_row=1)
    return DATA


def get_driver_fixture(request):
    return request.getfixturevalue("driver")


def pytest_generate_tests(metafunc):
    if "excel_case" in metafunc.fixturenames:
        cases = load_cases()
        metafunc.parametrize(
            "excel_case",
            cases,
            ids=[c["用例编号"] for c in cases],
        )


@allure.feature("Excel驱动")
@allure.story("ui_cases.xlsx 关键字驱动执行")
def test_excel_case(excel_case, request):
    case = excel_case
    mode = case.get("执行方式", "")
    node = case.get("关键字步骤/节点", "")
    if mode == "codecase":
        # 代码用例承载（复杂链路），Excel 登记追溯；避免重复执行直接跳过
        pytest.skip(f"代码用例承载: {node}")
    driver = get_driver_fixture(request)
    cfg = load_config()
    acct = cfg["account"]["admin"]
    ex = KeywordExecutor(driver, cfg["base_url"], acct)
    with allure.step(f"执行关键字步骤: {case.get('关键字步骤/节点')}"):
        ex.run_case(case.get("关键字步骤/节点", ""))

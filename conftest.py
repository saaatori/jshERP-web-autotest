# -*- coding: utf-8 -*-
"""pytest 入口夹具：driver 管理、会话级登录、失败取证钩子（计划 §3.2/§3.3）"""
import allure
import pytest

from utils.api_helper import JshApi
from utils.config import load_config
from utils.driver import create_driver
from utils.logger import get_logger
from page.login_page import LoginPage
from page.menu_frame import MenuFrame

log = get_logger(__name__)
_cfg = load_config()
_driver = None


@pytest.fixture(scope="session")
def cfg() -> dict:
    return _cfg


@pytest.fixture(scope="session")
def driver():
    global _driver
    _driver = create_driver(_cfg)
    yield _driver
    _driver.quit()


@pytest.fixture()
def admin_logged(driver):
    """管理员登录态保障（函数级）：login 等模块会登出会话，故每条用例前校验
    当前用户，非管理员登录态则重新登录。"""
    lp = LoginPage(driver)
    menu = MenuFrame(driver)
    need_login = True
    if "/user/login" not in driver.current_url:
        menu.open("/dashboard/analysis")
        menu.dismiss_popups()
        if "测试用户" in menu.welcome_text():
            need_login = False
    if need_login:
        if menu.is_present(menu.LOGOUT, timeout=2):
            menu.logout()
        lp.open()
        acct = _cfg["account"]["admin"]
        lp.login(acct["login_name"], acct["password"])
        assert lp.wait_login_success(), "管理员登录失败"
        lp.dismiss_popups()
    return driver


@pytest.fixture(scope="session")
def api(cfg) -> JshApi:
    """数据准备/清理通道（接口后门）。

    使用独立接口账号 uitest_api（管理员角色）：DEF-EXP-06 防攻击机制会对
    "同用户+同模块+同IP 同一秒"的第二次操作强制注销，全量回归时接口建数与
    浏览器操作同用户互踩导致会话连环失效（实测），故两个通道必须分账号。"""
    acct = cfg["account"]["api"]
    client = JshApi(cfg["api_base_url"], acct["login_name"], acct["password"])
    client.login()
    yield client


@pytest.fixture()
def bill_tracker(api):
    """登记用例中创建的单据，用例结束（无论成败）自动删除。

    用法：bill_tracker.append((("出库", "销售", number),))
    每个元素可给多个候选 (type, subType, number)，teardown 逐个尝试直到查到并删除。
    解决"断言失败 → 用例尾部内联清理被跳过"的残留问题。"""
    tracked = []
    yield tracked
    for candidates in tracked:
        for t, st, num in candidates:
            try:
                rows = api.list_bill(t, st, num)
            except Exception as e:  # noqa: BLE001 - 清理尽力而为
                log.warning("账单清理查询失败 %s/%s/%s: %s", t, st, num, e)
                continue
            if rows:
                try:
                    api.delete_bill(rows[0]["id"])
                except Exception as e:  # noqa: BLE001
                    log.warning("账单清理删除失败 %s: %s", num, e)
                break


@pytest.fixture(scope="session", autouse=True)
def _session_sweep(request):
    """会话结束兜底：按 UITEST 前缀扫删残留测试数据（不影响用例结果）。"""
    yield
    try:
        acct = _cfg["account"]["api"]
        client = JshApi(_cfg["api_base_url"], acct["login_name"], acct["password"])
        client.login()
        removed = client.sweep_test_data()
        if any(removed.values()):
            log.info("会话结束兜底清理: %s", removed)
    except Exception as e:  # noqa: BLE001 - 兜底失败不影响用例结果
        log.warning("会话结束兜底清理异常: %s", e)


@pytest.fixture(scope="session")
def master(api) -> dict:
    """主数据名称（供应商/客户/仓库/账户，动态解析）"""
    return api.master_data()


# ---- 失败取证：截图 + 页面源码（计划 §3.3 第4条 / §3.4）----
@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()
    if rep.when == "call" and rep.failed and _driver is not None:
        try:
            from page.base_page import BasePage
            bp = BasePage(_driver)
            shot = bp.screenshot(f"FAIL_{item.name}")
            page = bp.save_page_source(f"FAIL_{item.name}")
            allure.attach.file(shot, name="失败截图",
                               attachment_type=allure.attachment_type.PNG)
            allure.attach.file(page, name="页面源码",
                               attachment_type=allure.attachment_type.HTML)
            log.error("用例失败，已取证: %s", item.name)
        except Exception as e:  # noqa: BLE001 - 取证失败不影响报告
            log.error("失败取证异常: %s", e)

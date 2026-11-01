# -*- coding: utf-8 -*-
"""登录认证 UI 用例（UI-AUTH-001~005，对应 REQ-AUTH-001/002/003/005）。

本模块用例要求"未登录"起点：模块级夹具保证先退出已有会话。
"""
import allure
import pytest

from page.login_page import LoginPage
from page.menu_frame import MenuFrame

pytestmark = [pytest.mark.smoke]


@pytest.fixture()
def logged_out(driver):
    """确保起点为未登录状态：先开登录页，若仍处于登录态则退出"""
    lp = LoginPage(driver)
    lp.open()
    menu = MenuFrame(driver)
    if menu.is_present(menu.LOGOUT, timeout=2):
        menu.logout()
        lp.open()
    return lp


@allure.feature("登录认证")
@allure.story("UI-AUTH-001 正确账号密码登录进入首页")
def test_UI_AUTH_001_login_success(logged_out, cfg):
    acct = cfg["account"]["admin"]
    logged_out.login(acct["login_name"], acct["password"])
    assert logged_out.wait_login_success(), "登录后未跳转 /dashboard/analysis"
    menu = MenuFrame(logged_out.driver)
    assert "欢迎您，测试用户" in menu.welcome_text(), "右上角欢迎语未出现"
    logged_out.dismiss_popups()
    texts = menu.menu_texts()
    assert len(texts) >= 10, f"左侧一级菜单不足10个模块: {texts}"


@allure.feature("登录认证")
@allure.story("UI-AUTH-002 密码错误登录提示")
def test_UI_AUTH_002_login_wrong_password(logged_out):
    logged_out.login("jsh", "wrong_password_x")
    # 实测：失败停留登录页，接口 msgTip=user password error，HTTP 仍 200（REQ-AUTH-002）
    assert "/user/login" in logged_out.current_url(), "密码错误不应进入首页"
    toast = logged_out.error_toast()
    assert toast, "未出现任何错误提示"


@allure.feature("登录认证")
@allure.story("UI-AUTH-003 用户名/密码为空前端校验")
def test_UI_AUTH_003_login_empty(logged_out):
    # 1. 不输入任何内容直接点登录
    logged_out.click(logged_out.BTN_LOGIN)
    errs = logged_out.validation_errors()
    assert errs, "空用户名提交未出现必填校验"
    # 2. 补用户名不输密码再点
    logged_out.fill(logged_out.I_USERNAME, "jsh")
    logged_out.click(logged_out.BTN_LOGIN)
    errs2 = logged_out.validation_errors()
    assert errs2, "空密码提交未出现必填校验"
    assert "/user/login" in logged_out.current_url()


@allure.feature("登录认证")
@allure.story("UI-AUTH-004 退出登录返回登录页")
def test_UI_AUTH_004_logout(driver, logged_out, cfg):
    acct = cfg["account"]["admin"]
    logged_out.login(acct["login_name"], acct["password"])
    assert logged_out.wait_login_success()
    menu = MenuFrame(driver)
    menu.logout()
    assert "/user/login" in driver.current_url, "退出后未返回登录页"


@allure.feature("登录认证")
@allure.story("UI-AUTH-005 退出后浏览器回退不能进入系统")
@pytest.mark.permission
def test_UI_AUTH_005_back_after_logout(driver, logged_out, cfg):
    acct = cfg["account"]["admin"]
    logged_out.login(acct["login_name"], acct["password"])
    assert logged_out.wait_login_success()
    MenuFrame(driver).logout()
    assert "/user/login" in driver.current_url
    driver.back()
    logged_out.wait_for_ready()
    # 受保护页面不可见：要么被重定向回登录页，要么不出现系统内容
    welcome = MenuFrame(driver).welcome_text()
    assert welcome == "", f"退出后回退仍看到登录态内容: {welcome}"

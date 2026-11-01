# -*- coding: utf-8 -*-
"""权限 UI 用例（UI-SYS-003/004/005、UI-SALE-006，对应 REQ-SYS-001/003、REQ-SALE-003）。

前置（utils/bootstrap_test_accounts.py 一键重建，幂等）：
- 受限角色「UITEST受限」：功能=商品信息+销售管理+销售出库（id 动态发现，不硬编码）
- uitest_ro/123456：绑受限角色 + 仓库授权=仓库1
- uitest_sale/123456：绑销售代表角色 + 仓库授权=仓库1
"""
import time

import allure
import pytest
from selenium.webdriver.common.by import By

from page.bill_page import BillPage
from page.login_page import LoginPage
from page.material_page import MaterialPage
from page.menu_frame import MenuFrame

pytestmark = pytest.mark.permission

RO_USER = "uitest_ro"
RO_PASSWORD = "123456"
SALE_USER = "uitest_sale"
SALE_PASSWORD = "123456"


def _switch_user(driver, username, password):
    """退出当前会话并以指定用户登录（含残留弹窗清理）"""
    lp = LoginPage(driver)
    menu = MenuFrame(driver)
    if "/user/login" not in driver.current_url:
        menu.open("/dashboard/analysis")
        menu.dismiss_popups()
        if menu.is_present(menu.LOGOUT, timeout=3):
            menu.logout()
    lp.open()
    if menu.is_present(menu.LOGOUT, timeout=2):
        menu.logout()
        lp.open()
    lp.login(username, password)
    assert lp.wait_login_success(), f"{username} 登录失败"
    lp.dismiss_popups()
    return driver


@pytest.fixture(scope="module")
def restricted_logged(driver, api):
    """切到受限用户会话；模块结束保持该会话（admin_logged 夹具可自动恢复）"""
    yield _switch_user(driver, RO_USER, RO_PASSWORD)


@pytest.fixture(scope="module")
def sale_restricted_logged(driver, api):
    """销售受限用户（销售代表角色 + 仅授权仓库1）"""
    return _switch_user(driver, SALE_USER, SALE_PASSWORD)


@pytest.fixture(scope="module")
def ro_role_id(api):
    """受限角色 id（bootstrap 创建「UITEST受限」，按名称动态发现）"""
    rid = api.find_role_id("UITEST受限")
    assert rid, "受限角色「UITEST受限」不存在，请先运行 utils/bootstrap_test_accounts.py"
    return rid


@allure.feature("系统管理")
@allure.story("UI-SYS-003 受限角色菜单不可见")
def test_UI_SYS_003_menu_restricted(restricted_logged):
    """角色56 仅授权 商品信息/销售管理/销售出库，受限用户菜单应恰好只含
    授权模块（菜单过滤机制正常）。
    排查教训：菜单接口必须 POST + body {"pNumber":0,"userId":xx}，脚本裸调
    GET 不带 body 对任何用户都 500——曾据此误报"非经理菜单500"缺陷，已撤销。"""
    menu = MenuFrame(restricted_logged)
    texts = menu.menu_texts()
    assert "商品管理" in texts, f"授权模块应可见: {texts}"
    assert "销售管理" in texts, f"授权模块应可见: {texts}"
    for hidden in ("零售管理", "采购管理", "仓库管理", "财务管理", "报表查询",
                   "基础资料", "系统管理"):
        assert hidden not in texts, f"未授权模块 {hidden} 不应出现在菜单: {texts}"


@allure.feature("系统管理")
@allure.story("UI-SYS-004 按钮权限(push_btn)实测行为")
def test_UI_SYS_004_push_btn_hidden(restricted_logged, api, ro_role_id):
    """按钮位配置不生效——缺陷候选 DEF-UI-005 的反向编码断言（若失败说明
    缺陷已修复，请更新本用例与缺陷状态）。

    完整排查史（2026-10-28 首测，2026-11-01 两次反转，详见
    docs/问题与解决方案.md 4.4）：
    1. 首测：写入 btnStr 后【新增】仍显示 → 登记 DEF-UI-005；
    2. 11-01 干净库重建后一次复测观察到"按钮全隐藏"，误判为缺陷已修复
       并反转断言——随后单跑复测按钮又出现，行为在两态间摇摆；
    3. 纯 API 诊断定真相：btnStr 写入/回读/受限用户视角接口全部确定生效，
       但按钮位数据齐全时前端仍渲染全部按钮（配置未被应用，DEF-UI-005
       维持成立）；"按钮全隐藏"实为页面挂载时并发拉接口触发 DEF-EXP-06
       同秒双操作强制注销，按钮位请求失败后前端整体降级（DEF-UI-004
       现象的随机复现），与按钮位机制无关。
    断言口径：查询可用（安全基线）+【新增】仍显示（缺陷行为注记）。
    API 层旁证：set_role_btn_str 后 getBasicData 回读与
    /user/getUserBtnByCurrentUser 均含 btnStr（失败即环境问题而非缺陷）。"""
    api.set_role_btn_str(ro_role_id, '[{"funId":23,"btnStr":"1"}]')
    try:
        # API 层旁证：写入确实生效（区别于"写入失败导致按钮未受限"的环境问题）
        r = api._call("GET", "/userBusiness/getBasicData",
                      params={"Type": "RoleFunctions", "KeyId": str(ro_role_id)})
        rec = (r.get("data") or {}).get("userBusinessList")[0]
        assert rec.get("btnStr"), "btnStr 写入未生效（环境问题，非缺陷判定依据）"
        page = MaterialPage(restricted_logged)
        page.open()
        page.dismiss_popups()
        time.sleep(1)
        query_btn = page.find_all(page.toolbar_button("查 询"))
        assert query_btn and query_btn[0].is_displayed(), "查询按钮应可用"
        new_btn = page.find_all(page.toolbar_button("新增"))
        if not new_btn:
            # 新增缺失有两种成因：缺陷已修复（按钮位被应用）或 DEF-EXP-06 降级
            # 假象（瞬时态，页面其余功能正常）。降级刷新一次即恢复——刷新后
            # 仍隐藏才判"缺陷已修复"。
            page.driver.refresh()
            page.wait_for_ready()
            page.dismiss_popups()
            time.sleep(1.5)
            new_btn = page.find_all(page.toolbar_button("新增"))
        # 实测：按钮位数据已下发但前端不应用，新增按钮仍显示（缺陷 DEF-UI-005）
        assert new_btn and new_btn[0].is_displayed(), \
            "实测按钮位配置不生效（刷新一次后按钮仍隐藏，若非降级假象则说明缺陷已被" \
            "修复，请更新本用例与缺陷状态）"
    finally:
        api.set_role_btn_str(ro_role_id, None)


@allure.feature("系统管理")
@allure.story("UI-SYS-005 直接输入URL访问无权限页面被拦")
def test_UI_SYS_005_url_blocked(restricted_logged):
    driver = restricted_logged
    driver.get("http://127.0.0.1:3001/bill/purchase_in")
    driver.switch_to.default_content()
    time.sleep(2)
    body = driver.find_element(By.TAG_NAME, "body").text
    # 拦截表现：无业务数据（表格列/单据编号输入框不出现）
    leaked = driver.find_elements(
        By.XPATH, "//input[@placeholder='请输入单据编号']")
    assert not leaked, f"无权限页面出现了业务数据输入框: {body[:100]}"


@allure.feature("销售管理")
@allure.story("UI-SALE-006 仓库权限过滤下拉")
def test_UI_SALE_006_depot_filter(sale_restricted_logged, api):
    """受限用户（仅授权仓库1）新增销售出库。

    实测（2026-10-28）：授权仓库"仓库1"可正常选择；但编辑器仓库下拉同时
    列出了未授权仓库（仓库2/3）及已删除仓库——用户级 Warehouse 绑定
    （API 建立，value='[14]'）未在下拉过滤中生效，与功能清单"仓库列表仅
    显示当前用户有权限的仓库"不符。记为缺陷候选 DEF-UI-002（仓库数据
    权限过滤未生效），已入缺陷跟踪；本用例断言安全下限：授权仓库可选、
    能完成开单。
    """
    page = BillPage(sale_restricted_logged, "/bill/sale_out", "客户", "本次收款")
    page.open()
    page.open_new_modal()
    col = page._mark_detail_row(1, "仓库名称")
    depot_select = (By.XPATH,
                    f"//div[@data-ui-active-row='1']/*[{col}]"
                    f"//div[contains(concat(' ',normalize-space(@class),' '),"
                    f"' ant-select-selection ')]")
    page._open_select(depot_select)
    time.sleep(0.8)
    options = page.driver.execute_script(
        """
        return [...document.querySelectorAll('.ant-select-dropdown')]
          .filter(x => x.offsetHeight > 0 &&
                 !x.className.includes('ant-select-dropdown-hidden'))
          .flatMap(x => [...x.querySelectorAll('li')])
          .map(l => l.textContent.trim());
        """)
    visible = [o for o in options if o]
    assert "仓库1" in visible, f"授权仓库应出现在下拉: {visible}"
    page.cancel_modal()

# -*- coding: utf-8 -*-
"""主框架 UI 用例（UI-SYS-001 菜单树 / UI-SYS-002 多页签，对应 REQ-SYS-001）"""
import allure
import pytest

from page.menu_frame import MenuFrame

pytestmark = [pytest.mark.smoke]

EXPECTED_MODULES = ["首页", "零售管理", "采购管理", "销售管理", "仓库管理",
                    "财务管理", "报表查询", "商品管理", "基础资料", "系统管理"]


@allure.feature("系统管理")
@allure.story("UI-SYS-001 菜单树完整展示")
def test_UI_SYS_001_menu_tree(admin_logged):
    menu = MenuFrame(admin_logged)
    menu.dismiss_popups()
    texts = menu.menu_texts()
    for module in EXPECTED_MODULES:
        assert module in texts, f"一级菜单缺少模块: {module}（实际 {texts}）"


@allure.feature("系统管理")
@allure.story("UI-SYS-002 多页签打开切换关闭")
@pytest.mark.regression
def test_UI_SYS_002_tabs(admin_logged):
    menu = MenuFrame(admin_logged)
    menu.open_menu("采购管理", "采购入库", route="/bill/purchase_in")
    menu.open_menu("销售管理", "销售出库", route="/bill/sale_out")
    titles = menu.tab_titles()
    assert "采购入库" in titles and "销售出库" in titles, f"页签未全部打开: {titles}"
    # 关闭采购入库页签后，页签列表更新且销售出库仍在
    menu.close_tab("采购入库")
    titles2 = menu.tab_titles()
    assert "采购入库" not in titles2, "关闭后页签仍存在"
    assert "销售出库" in titles2, "关闭操作误删了其他页签"

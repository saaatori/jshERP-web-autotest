# -*- coding: utf-8 -*-
"""基础资料 UI 用例（UI-BAS-001/002/004/005，对应 REQ-BAS-001/003）"""
import allure
import pytest

from page.crud_page import CustomerPage, DepotPage, VendorPage

pytestmark = pytest.mark.usefixtures("admin_logged")
RUN = str(int(__import__("time").time()))[-6:]


@pytest.fixture()
def vendor_page(admin_logged):
    page = VendorPage(admin_logged)
    page.open()
    return page


@pytest.fixture()
def customer_page(admin_logged):
    page = CustomerPage(admin_logged)
    page.open()
    return page


@pytest.fixture()
def depot_page(admin_logged):
    page = DepotPage(admin_logged)
    page.open()
    return page


def _cleanup_supplier(api, name, ptype):
    """供应商/客户删除（尽力而为，接口路径与 material 同构）"""
    import json as _json
    data = api._call("GET", "/supplier/list", params={
        "search": _json.dumps({"type": ptype}, ensure_ascii=False),
        "currentPage": "1", "pageSize": "20"})
    for r in data.get("data", {}).get("rows", []):
        if r.get("supplier") == name:
            api._call("DELETE", f"/supplier/deleteBatch?ids={r['id']},")
            return True
    return False


@allure.feature("基础资料")
@allure.story("UI-BAS-001 新增供应商成功")
@pytest.mark.smoke
def test_UI_BAS_001_new_vendor(vendor_page, api):
    name = f"UITEST供应商{RUN}"
    vendor_page.create({"名称": name, "联系人": "联系人A",
                        "手机号码": "13800000000"})
    vendor_page.query(name)
    row = vendor_page.row(name)
    assert row, f"新增供应商后列表未查到 {name}"
    _cleanup_supplier(api, name, "供应商")


@allure.feature("基础资料")
@allure.story("UI-BAS-002 供应商重名提示")
@pytest.mark.regression
def test_UI_BAS_002_duplicate_vendor(vendor_page, api):
    name = f"UITEST供应商{RUN}"
    # 先确保存在同名供应商
    vendor_page.query(name)
    if not vendor_page.row(name):
        vendor_page.create({"名称": name})
    msg = vendor_page.create_expect_error({"名称": name})
    assert msg, "重名保存被拒时应出现提示"
    _cleanup_supplier(api, name, "供应商")


@allure.feature("基础资料")
@allure.story("UI-BAS-004 新增客户成功")
@pytest.mark.regression
def test_UI_BAS_004_new_customer(customer_page, api):
    name = f"UITEST客户{RUN}"
    customer_page.create({"名称": name, "联系人": "联系人B"})
    customer_page.query(name)
    row = customer_page.row(name)
    assert row, f"新增客户后列表未查到 {name}"
    _cleanup_supplier(api, name, "客户")


@allure.feature("基础资料")
@allure.story("UI-BAS-005 新增仓库成功")
@pytest.mark.regression
def test_UI_BAS_005_new_depot(depot_page, api):
    name = f"UITEST仓库{RUN}"
    depot_page.create({"仓库名称": name, "仓库地址": "测试地址", "排序": "9"})
    depot_page.query(name)
    row = depot_page.row(name)
    assert row, f"新增仓库后列表未查到 {name}"
    # 仓库删除走 /depot/deleteBatch（无引用时可删）
    data = api._call("GET", "/depot/list")
    for r in data.get("data", {}).get("rows", []):
        if r.get("name") == name:
            api._call("DELETE", f"/depot/deleteBatch?ids={r['id']},")

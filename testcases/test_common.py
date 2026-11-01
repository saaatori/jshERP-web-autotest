# -*- coding: utf-8 -*-
"""通用交互 UI 用例（UI-COM-001 弹窗确认与取消，对应 NFR-USE-002）。

AntD Modal 确认框封装（BasePage.confirm_dialog）已随删除/审核等操作验证，
本用例以删除场景独立验证"确认执行、取消不执行"。
"""
import json
import time

import allure
import pytest
from selenium.webdriver.common.by import By

from page.crud_page import VendorPage

pytestmark = pytest.mark.usefixtures("admin_logged")

RUN = str(int(time.time()))[-6:]


@pytest.fixture()
def com_page(admin_logged):
    page = VendorPage(admin_logged)
    page.open()
    return page


def _create_vendor(api, name):
    r = api._call("POST", "/supplier/add", body={
        "type": "供应商", "supplier": name, "contacts": "测COM",
        "phonenum": "", "email": "", "sort": "9", "remark": "UITEST"})
    assert isinstance(r, dict) and r.get("code") == 200, f"建供应商失败: {r}"
    time.sleep(1.3)
    data = api._call("GET", "/supplier/list", params={
        "search": json.dumps({"type": "供应商", "supplier": name},
                             ensure_ascii=False),
        "currentPage": "1", "pageSize": "5"})
    rows = data.get("data", {}).get("rows", [])
    assert rows, f"供应商未建成功: {name}"
    return rows[0]["id"]


def _delete_via_api(api, vendor_id):
    api._call("DELETE", f"/supplier/deleteBatch?ids={vendor_id},")


@allure.feature("通用交互")
@allure.story("UI-COM-001 弹窗确认与取消行为")
@pytest.mark.regression
def test_UI_COM_001_confirm_cancel(com_page, api):
    """存在可删除数据：删除→确认=执行；删除→取消=不执行（AntD Modal 验证）。"""
    name_del = f"UITEST确认删{RUN}"
    name_keep = f"UITEST取消删{RUN}"
    vid_del = _create_vendor(api, name_del)
    vid_keep = _create_vendor(api, name_keep)
    try:
        # 场景1：删除 → 确认 → 行消失
        com_page.query(name_del)
        com_page.check_row(name_del)
        com_page.click(com_page.toolbar_button("删除"))
        time.sleep(1)
        assert com_page.confirm_dialog(), "删除确认框未出现"
        time.sleep(1.2)
        com_page.query(name_del)
        assert not com_page.row(name_del), f"确认删除后行仍存在: {name_del}"

        # 场景2：删除 → 取消 → 行保留
        com_page.query(name_keep)
        com_page.check_row(name_keep)
        com_page.click(com_page.toolbar_button("删除"))
        time.sleep(1)
        cancel_btn = (By.XPATH, "//div[contains(@class,'ant-modal-confirm')]"
                                "//button[normalize-space()='取 消']")
        assert com_page.is_present(cancel_btn, 3), "删除确认框未出现"
        com_page.click(cancel_btn)
        time.sleep(1.2)
        com_page.query(name_keep)
        row = com_page.row(name_keep)
        assert row, f"取消删除后行不应消失: {name_keep}"
    finally:
        for vid in (vid_del, vid_keep):
            _delete_via_api(api, vid)

# -*- coding: utf-8 -*-
"""商品管理 UI 用例（UI-GOODS-001~004，对应 REQ-GOODS-002 / NFR-USE-001）"""
import time

import allure
import pytest

from page.material_page import MaterialPage

pytestmark = pytest.mark.usefixtures("admin_logged")
RUN = str(int(__import__("time").time()))[-6:]
NAME = f"UITEST商品{RUN}"
BARCODE = f"UIT{RUN}"


@pytest.fixture()
def material_page(admin_logged):
    page = MaterialPage(admin_logged)
    page.open()
    return page


@pytest.fixture(scope="module")
def material_id(api):
    """模块级数据：API 预置一个商品供 002/004 使用，teardown 清理"""
    resp = api.add_material(NAME, BARCODE)
    row = api.find_material(NAME)
    assert row, f"API 预置商品失败: add响应={resp}"
    yield row["id"]
    api.delete_material(row["id"])


@allure.feature("商品管理")
@allure.story("UI-GOODS-001 新增商品成功")
@pytest.mark.smoke
def test_UI_GOODS_001_new_material(material_page, api):
    name = f"UITEST商品U{RUN}"
    barcode = f"UITU{RUN}"
    material_page.create(name, unit="个", barcode=barcode,
                         purchase="10", sale="20", low="20")
    material_page.query(name)
    row = material_page.row_by_name(name)
    assert row, f"新增后列表未查到 {name}"
    assert row.get("条码") == barcode, f"条码列不一致: {row}"
    assert row.get("状态") == "启用", f"新商品默认应为启用: {row}"
    # teardown：删除 UI 建的商品
    found = api.find_material(name)
    if found:
        api.delete_material(found["id"])


@allure.feature("商品管理")
@allure.story("UI-GOODS-002 条码重复提示(红框+悬浮Tooltip)")
@pytest.mark.regression
def test_UI_GOODS_002_duplicate_barcode(material_page, material_id, api):
    """重复条码保存被拦截，且条码输入框出现 antd Tooltip 提示"该条码已经存在"
    （前端先调 checkIsBarCodeExist 校验，通过后聚焦标红+Tooltip）。
    排查教训：该提示形态为 Tooltip（非 toast/表单文案），曾因只查
    message/notification/form-explain 而误报"无提示"(原 DEF-UI-001，已撤销)。"""
    material_page.open_create_modal()
    material_page.click(material_page.M_TAB_STOCK)
    time.sleep(0.5)
    for label, value in {
        "名称": f"UITEST重复{RUN}", "单位": "个", "条码": BARCODE,
        "采购价": "10", "零售价": "20", "销售价": "20", "最低售价": "20",
    }.items():
        material_page.fill(material_page.M_LABELS[label], value)
    material_page.click(material_page.M_BTN_SAVE)
    # 提示证据：antd Tooltip 文案"该条码已经存在"（弹窗保持打开期间轮询）
    tip_text = ""
    deadline = time.time() + 5
    while time.time() < deadline:
        tip = material_page.driver.execute_script(
            "const t=document.querySelector('.ant-tooltip');"
            "return t ? t.textContent.trim() : '';")
        if tip:
            tip_text = tip
            break
        time.sleep(0.4)
    assert "已经存在" in tip_text, f"重复条码应出现Tooltip提示, 实际: {tip_text!r}"
    # 弹窗保持打开（保存被拦截），取消退出
    if material_page.is_present(material_page.M_BTN_CANCEL, timeout=2):
        material_page.click(material_page.M_BTN_CANCEL)
    time.sleep(0.8)
    # 被拦截证据：API 侧不存在该重名商品
    found = api.find_material(f"UITEST重复{RUN}")
    assert found is None, "重复条码不应保存成功"
    original = api.find_material(NAME)
    assert original and original["id"] == material_id


@allure.feature("商品管理")
@allure.story("UI-GOODS-003 必填项为空前端校验与红星标识")
@pytest.mark.regression
def test_UI_GOODS_003_required_validation(material_page):
    errs = material_page.save_expect_validation()
    assert errs, "名称留空保存未出现必填校验"


@allure.feature("商品管理")
@allure.story("UI-GOODS-004 商品启用/停用切换")
@pytest.mark.regression
def test_UI_GOODS_004_enable_disable(material_page, material_id):
    material_page.set_enabled(NAME, enable=False)
    row = material_page.row_by_name(NAME)
    assert row and row.get("状态") == "禁用", f"停用后状态未变: {row}"
    material_page.set_enabled(NAME, enable=True)
    row = material_page.row_by_name(NAME)
    assert row and row.get("状态") == "启用", f"启用后状态未恢复: {row}"

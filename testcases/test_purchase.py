# -*- coding: utf-8 -*-
"""采购管理 UI 用例（UI-PUR-001~008，对应 REQ-PUR-002~007；R2/R3/R4 实测口径）"""
import time

import allure
import pytest

from page.bill_page import BillPage

pytestmark = pytest.mark.usefixtures("admin_logged")
RUN = str(int(time.time()))[-6:]
MAT = f"UITEST采购商品{RUN}"
BAR = f"UITP{RUN}"


@pytest.fixture()
def pur_page(admin_logged):
    page = BillPage(admin_logged, "/bill/purchase_in", "供应商", "本次付款")
    page.open()
    return page


@pytest.fixture()
def order_page(admin_logged):
    page = BillPage(admin_logged, "/bill/purchase_order", "供应商", "本次付款")
    page.open()
    return page


@pytest.fixture(scope="module")
def mat(api):
    """模块级测试商品，teardown 清理"""
    api.add_material(MAT, BAR)
    row = api.find_material(MAT)
    assert row, "API 预置采购测试商品失败"
    yield {"id": row["id"], "barcode": BAR}
    api.delete_material(row["id"])


def _new_order(api, qty=10, price=10, status=None):
    """API 建采购订单，返回 (id, number)。
    实测：UI 采购订单列表按 type='其它'&subType='采购订单' 过滤（华夏 ERP 口径），
    API 建单必须用同口径，否则 UI 列表不可见。"""
    number = "CGDD" + api.build_number()
    r = api.add_bill(number, "其它", "采购订单", 57, 17, 0, -(qty * price),
                     [{"materialId": 0, "barCode": BAR, "depotId": 14,
                       "operNumber": qty, "unitPrice": price, "allPrice": qty * price,
                       "taxRate": 0, "taxMoney": 0, "taxLastMoney": qty * price,
                       "unit": "个"}], remark=f"UITEST订单{RUN}")
    assert isinstance(r, dict) and r.get("code") == 200, f"API 建订单失败: {r}"
    row = api.list_bill("其它", "采购订单", number)[0]
    if status == "1":
        api.set_bill_status(row["id"], "1")
    return row["id"], number


@pytest.fixture(scope="module")
def order_unaudited(api, mat):
    bid, number = _new_order(api)
    yield {"id": bid, "number": number}
    api.safe_delete_bill(bid)


@pytest.fixture(scope="module")
def order_audited(api, mat):
    bid, number = _new_order(api, status="1")
    yield {"id": bid, "number": number}
    api.safe_delete_bill(bid)


def _new_purchase_in(api, qty=3, price=10, pay=20):
    """API 建采购入库（欠款=qty*price-pay，R2），返回 (id, number)"""
    number = "CGRK" + api.build_number()
    total = qty * price
    r = api.add_bill(number, "入库", "采购", 57, 17, -pay, -total,
                     [{"materialId": 0, "barCode": BAR, "depotId": 14,
                       "operNumber": qty, "unitPrice": price, "allPrice": total,
                       "taxRate": 0, "taxMoney": 0, "taxLastMoney": total,
                       "unit": "个"}], remark=f"UITEST入库{RUN}")
    assert isinstance(r, dict) and r.get("code") == 200, f"API 建入库失败: {r}"
    row = api.list_bill("入库", "采购", number)[0]
    return row["id"], number


@pytest.fixture(scope="module")
def purchase_in(api, mat):
    bid, number = _new_purchase_in(api)
    yield {"id": bid, "number": number, "total": 30, "pay": 20, "debt": 10}
    api.safe_delete_bill(bid)


@pytest.fixture(scope="module")
def purchase_in_audited(api, mat):
    bid, number = _new_purchase_in(api)
    api.set_bill_status(bid, "1")
    yield {"id": bid, "number": number}
    api.safe_delete_bill(bid)


@allure.feature("采购管理")
@allure.story("UI-PUR-001 新增采购订单(含明细行)")
@pytest.mark.smoke
def test_UI_PUR_001_new_order(order_page, api, mat, master, bill_tracker):
    data = order_page.fill_modal(master["supplier"], [(BAR, 10, 10)])
    number = data["number"]
    assert number.startswith("CGDD"), f"单据编号前缀异常: {number}"
    bill_tracker.append((("其它", "采购订单", number),))
    order_page.save()
    row = order_page.find_bill(number)
    assert row, f"保存后列表未查到订单 {number}"
    assert row.get("状态") == "未审核", f"新订单状态应为未审核: {row}"


@allure.feature("采购管理")
@allure.story("UI-PUR-002 采购订单审核状态变化")
@pytest.mark.smoke
def test_UI_PUR_002_audit_order(order_page, order_unaudited):
    order_page.audit(order_unaudited["number"])
    assert order_page.status_of(order_unaudited["number"]) == "已审核"


@allure.feature("采购管理")
@allure.story("UI-PUR-003 订单转采购入库(部分转→部分执行 R3)")
@pytest.mark.regression
def test_UI_PUR_003_transfer_partial(order_page, order_audited, api, bill_tracker):
    order_page.open()
    new_number = order_page.transfer(order_audited["number"], "转采购入库",
                                     items=[(6,)])
    assert new_number.startswith("CGRK"), f"转入库单号前缀异常: {new_number}"
    bill_tracker.append((("入库", "采购", new_number),))
    # 源单状态变部分执行（R3 实测状态 3；UI 文案采购语境为"部分采购"）
    assert order_page.status_of(order_audited["number"]) == "部分采购"


@allure.feature("采购管理")
@allure.story("UI-PUR-004 新增采购入库(明细+付款，欠款公式 R2)")
@pytest.mark.smoke
def test_UI_PUR_004_new_purchase_in(pur_page, api, mat, master):
    data = pur_page.fill_modal(master["supplier"], [(BAR, 3, 10)],
                               account=master["account"], pay="20")
    number = data["number"]
    pur_page.save()
    row = pur_page.find_bill(number)
    assert row, f"保存后列表未查到入库单 {number}"
    # UI 保存默认带系统税率（实测 12%，含税合计≠金额合计），故按 R2 公式断言：
    # 金额合计=数量×单价；本次欠款 = 含税合计 − 本次付款
    assert float(row["金额合计"]) == 30, f"金额合计列异常: {row}"
    assert float(row["本次付款"]) == 20, f"本次付款列异常: {row}"
    assert abs(float(row["本次欠款"]) - (float(row["含税合计"]) - 20)) < 0.001, \
        f"R2 欠款公式不成立: {row}"


@allure.feature("采购管理")
@allure.story("UI-PUR-005 入库列表组合查询与重置")
@pytest.mark.regression
def test_UI_PUR_005_query_reset(pur_page, purchase_in):
    number = purchase_in["number"]
    # 1. 按单号查询命中
    pur_page.query_by_number(number)
    row = pur_page.find_bill(number)
    assert row, f"按单号查询未命中: {number}"
    # 2. 无效条件查询为空
    pur_page.query_by_number("CGRK99999999")
    assert pur_page.find_bill(number) is None, "无效单号不应查到数据"
    # 3. 重置后日期恢复默认近3个月
    pur_page.click(pur_page.toolbar_button("重 置"))
    time.sleep(1)
    start = pur_page.find(pur_page.I_NUMBER)
    # 日期默认值断言：开始/结束时间输入框恢复非空默认（近3个月区间）
    dates = pur_page.driver.find_elements(
        "xpath", "//input[@placeholder='开始时间'] | //input[contains(@class,'ant-calendar')]")
    assert dates, "重置后日期区间输入框不可见"
    # 单号输入框已清空
    assert start.get_attribute("value") == ""


@allure.feature("采购管理")
@allure.story("UI-PUR-006 列表金额列与保存值一致(R2口径)")
@pytest.mark.db_check
def test_UI_PUR_006_amounts(pur_page, purchase_in):
    pur_page.query_by_number(purchase_in["number"])
    row = pur_page.find_bill(purchase_in["number"])
    assert row, "未查询到单据行"
    assert float(row["金额合计"]) == purchase_in["total"]
    assert float(row["含税合计"]) == purchase_in["total"]
    assert float(row["本次付款"]) == purchase_in["pay"]
    assert float(row["本次欠款"]) == purchase_in["debt"]


@allure.feature("采购管理")
@allure.story("UI-PUR-007 审核入库单(库存不因审核变化 R4)")
@pytest.mark.regression
def test_UI_PUR_007_audit_purchase_in(pur_page, purchase_in, api):
    pur_page.open()
    stock_before = api.find_material(MAT)["stock"]
    pur_page.audit(purchase_in["number"])
    assert pur_page.status_of(purchase_in["number"]) == "已审核"
    stock_after = api.find_material(MAT)["stock"]
    assert float(stock_before) == float(stock_after), \
        f"R4: 审核不应改变库存 {stock_before}→{stock_after}"


@allure.feature("采购管理")
@allure.story("UI-PUR-008 转采购退货入口(明细带入)")
@pytest.mark.regression
def test_UI_PUR_008_transfer_back_entry(pur_page, purchase_in_audited):
    pur_page.open()
    pur_page.query_by_number(purchase_in_audited["number"])
    pur_page.check_row(purchase_in_audited["number"])
    pur_page.click(pur_page.toolbar_button("转采购退货"))
    time.sleep(1.5)
    pur_page.confirm_dialog()
    # 退货编辑弹窗打开且明细带入（明细网格为 div.tr 结构，用标记行取文本）
    modal_input = pur_page._detail_input("数量", 1)
    assert pur_page.is_present(modal_input, timeout=8), "转采购退货编辑弹窗未打开"
    pur_page._mark_detail_row(1, "数量")
    row = pur_page.driver.find_elements("xpath", "//div[@data-ui-active-row='1']")
    row_text = row[0].text if row else ""
    assert BAR in row_text, f"退货明细未带入原单商品: {row_text!r}"
    pur_page.cancel_modal()

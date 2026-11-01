# -*- coding: utf-8 -*-
"""销售管理 UI 用例（UI-SALE-001~007，对应 REQ-SALE-001~006；R1/R2/R3 实测口径）"""
import time

import allure
import pytest
from selenium.webdriver.common.by import By

from page.bill_page import BillPage

pytestmark = pytest.mark.usefixtures("admin_logged")
RUN = str(int(time.time()))[-6:]
MAT = f"UITEST销售商品{RUN}"
BAR = f"UITS{RUN}"
STOCK_QTY = 50


@pytest.fixture()
def sale_page(admin_logged):
    page = BillPage(admin_logged, "/bill/sale_out", "客户", "本次收款")
    page.open()
    return page


@pytest.fixture()
def sale_order_page(admin_logged):
    page = BillPage(admin_logged, "/bill/sale_order", "客户", "本次收款")
    page.open()
    return page


@pytest.fixture(scope="module")
def sale_mat(api):
    """模块级测试商品：建商品 + 其它入库 50 个（teardown 删商品自动回退库存）"""
    api.add_material(MAT, BAR)
    row = api.find_material(MAT)
    assert row, "API 预置销售测试商品失败"
    r = api.add_stock(BAR, STOCK_QTY)
    assert isinstance(r, dict) and r.get("code") == 200, f"补库存失败: {r}"
    time.sleep(1.3)
    yield {"id": row["id"], "barcode": BAR}
    api.delete_material(row["id"])


def _new_sale_order(api, qty=10, price=20, status=None):
    """API 建销售订单（type='其它' 口径，同采购订单），返回 (id, number)"""
    number = "XSDD" + api.build_number()
    r = api.add_bill(number, "其它", "销售订单", 58, 17, 0, -(qty * price),
                     [{"materialId": 0, "barCode": BAR, "depotId": 14,
                       "operNumber": qty, "unitPrice": price, "allPrice": qty * price,
                       "taxRate": 0, "taxMoney": 0, "taxLastMoney": qty * price,
                       "unit": "个"}], remark=f"UITEST销售订单{RUN}")
    assert isinstance(r, dict) and r.get("code") == 200, f"API 建销售订单失败: {r}"
    row = api.list_bill("其它", "销售订单", number)[0]
    if status == "1":
        api.set_bill_status(row["id"], "1")
    return row["id"], number


@pytest.fixture(scope="module")
def sale_order_audited(api, sale_mat):
    bid, number = _new_sale_order(api, status="1")
    yield {"id": bid, "number": number}
    api.safe_delete_bill(bid)


def _new_sale_out(api, qty=5, price=20, pay=0, status=None):
    """API 建销售出库（type='出库'/subType='销售'），返回 (id, number)"""
    number = "XSCK" + api.build_number()
    total = qty * price
    r = api.add_bill(number, "出库", "销售", 58, 17, pay, -total,
                     [{"materialId": 0, "barCode": BAR, "depotId": 14,
                       "operNumber": qty, "unitPrice": price, "allPrice": total,
                       "taxRate": 0, "taxMoney": 0, "taxLastMoney": total,
                       "unit": "个"}], remark=f"UITEST销售出库{RUN}")
    assert isinstance(r, dict) and r.get("code") == 200, f"API 建销售出库失败: {r}"
    row = api.list_bill("出库", "销售", number)[0]
    if status == "1":
        api.set_bill_status(row["id"], "1")
    return row["id"], number


@allure.feature("销售管理")
@allure.story("UI-SALE-001 新增销售订单")
@pytest.mark.smoke
def test_UI_SALE_001_new_order(sale_order_page, api, sale_mat, master, bill_tracker):
    data = sale_order_page.fill_modal(master["customer"], [(BAR, 10, 20)])
    number = data["number"]
    assert number.startswith("XSDD"), f"单据编号前缀异常: {number}"
    bill_tracker.append((("其它", "销售订单", number),))
    sale_order_page.save()
    row = sale_order_page.find_bill(number)
    assert row, f"保存后列表未查到销售订单 {number}"
    assert row.get("状态") == "未审核"


@allure.feature("销售管理")
@allure.story("UI-SALE-002 销售订单转销售出库(部分转 R3)")
@pytest.mark.regression
def test_UI_SALE_002_transfer_partial(sale_order_page, sale_order_audited, api, bill_tracker):
    sale_order_page.open()
    new_number = sale_order_page.transfer(sale_order_audited["number"],
                                          "转销售出库", items=[(6,)])
    bill_tracker.append((("出库", "销售", new_number),))
    assert new_number.startswith("XSCK"), f"转出库单号前缀异常: {new_number}"
    status = sale_order_page.status_of(sale_order_audited["number"])
    # R3：源单状态 3；UI 文案销售语境为"部分销售"
    assert status in ("部分销售", "部分执行"), f"源单状态异常: {status}"


@allure.feature("销售管理")
@allure.story("UI-SALE-003 新增销售出库(收款+库存扣减 R2)")
@pytest.mark.smoke
def test_UI_SALE_003_new_sale_out(sale_page, api, sale_mat, master, bill_tracker):
    stock_before = float(api.find_material(MAT)["stock"])
    data = sale_page.fill_modal(master["customer"], [(BAR, 3, 20)],
                                account=master["account"], pay="20")
    number = data["number"]
    bill_tracker.append((("出库", "销售", number),))
    sale_page.save()
    row = sale_page.find_bill(number)
    assert row, f"保存后列表未查到销售出库 {number}"
    assert float(row["金额合计"]) == 60, f"金额合计列异常: {row}"
    assert abs(float(row["本次欠款"]) - (float(row["含税合计"]) - 20)) < 0.001, \
        f"R2 欠款公式不成立: {row}"
    time.sleep(1.3)
    stock_after = float(api.find_material(MAT)["stock"])
    assert abs(stock_after - (stock_before - 3)) < 0.001, \
        f"库存应减 3: {stock_before}→{stock_after}"


@allure.feature("销售管理")
@allure.story("UI-SALE-004 超库存出库拦截(minus_stock_flag=0, R1)")
@pytest.mark.regression
def test_UI_SALE_004_over_stock_blocked(sale_page, api, sale_mat, master):
    """翻转 minus_stock_flag=0 → 出库数量超库存被 8000004 拦截；teardown 恢复 1。
    断言口径：保存被拦（弹窗未关闭）且系统未产生出库单。"""
    api.set_minus_stock_flag("0")
    try:
        stock_before = float(api.find_material(MAT)["stock"])
        data = sale_page.fill_modal(master["customer"],
                                    [(BAR, stock_before + 10, 20)],
                                    account=master["account"], pay="0")
        number = data["number"]
        # 点击保存 → 被 8000004 拦截：弹窗保持打开、无出库单产生
        sale_page.click(sale_page.M_BTN_SAVE)
        time.sleep(2)
        sale_page.mark_modal()
        modal_still_open = sale_page.is_present(
            (By.XPATH, "//div[@data-ui-active-modal='1']"
                       "//input[@placeholder='请输入单据编号']"), 3)
        sale_page.cancel_modal()
        time.sleep(1)
        rows = api.list_bill("出库", "销售", number)
        assert not rows, f"超库存出库不应保存成功: {rows}"
        assert modal_still_open, "保存被拦时编辑器应保持打开"
    finally:
        api.set_minus_stock_flag("1")
        assert api.get_system_config()["minusStockFlag"] == "1", "开关未恢复"


@allure.feature("销售管理")
@allure.story("UI-SALE-005 出库单价低于最低售价拦截(8500018)")
@pytest.mark.regression
def test_UI_SALE_005_low_price_blocked(sale_page, api, sale_mat, master):
    """商品 low_decimal=20，出库单价 15 保存被 8500018 拦截（R1 实测）"""
    stock_before = float(api.find_material(MAT)["stock"])
    data = sale_page.fill_modal(master["customer"], [(BAR, 1, 15)],
                                account=master["account"], pay="0")
    number = data["number"]
    # 点击保存 → 8500018 拦截（提示文案出现即读，antd message 3 秒消失）
    sale_page.click(sale_page.M_BTN_SAVE)
    time.sleep(1)
    msg = sale_page.message_text()
    time.sleep(0.5)
    sale_page.mark_modal()
    modal_still_open = sale_page.is_present(
        (By.XPATH, "//div[@data-ui-active-modal='1']"
                   "//input[@placeholder='请输入单据编号']"), 2)
    if modal_still_open:
        sale_page.cancel_modal()
    rows = api.list_bill("出库", "销售", number)
    assert not rows, f"低于最低售价出库不应保存成功: {rows}"
    assert (msg or modal_still_open), "保存应被拦截（有提示或弹窗保持打开）"
    stock_after = float(api.find_material(MAT)["stock"])
    assert abs(stock_after - stock_before) < 0.001, "库存不应变化"


@allure.feature("销售管理")
@allure.story("UI-SALE-007 销售退货关联原单(库存回补)")
@pytest.mark.regression
def test_UI_SALE_007_sale_return(sale_page, api, sale_mat, master, bill_tracker):
    sale_page.open()
    stock_before = float(api.find_material(MAT)["stock"])
    # 实测：未审核出库不能转退货（toast"该状态不能转销售退货"），须先审核
    bid, number = _new_sale_out(api, qty=10, price=20, pay=0, status="1")
    bill_tracker.append((("出库", "销售", number),))
    time.sleep(1.3)
    stock_after_out = float(api.find_material(MAT)["stock"])
    assert abs(stock_after_out - (stock_before - 10)) < 0.001

    # UI 勾选出库单 → 转销售退货 → 编辑器带入 → 保存（复用 transfer 的健壮流程）
    ret_number = sale_page.transfer(number, "转销售退货")
    # UI 建的退货单 remark 为空，兜底 sweep 扫不到；候选两种 type/subType 口径
    bill_tracker.append((("入库", "销售退货", ret_number),
                         ("其它", "销售退货", ret_number)))
    time.sleep(1.3)
    stock_after_ret = float(api.find_material(MAT)["stock"])
    assert abs(stock_after_ret - stock_before) < 0.001, \
        f"退货后库存应回补至原值: {stock_after_out}→{stock_after_ret}"
    # teardown：源出库单已审核需反审核再删，走 safe_delete_bill（tracker 只会直接删）
    api.safe_delete_bill(bid)

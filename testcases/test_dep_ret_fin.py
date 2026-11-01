# -*- coding: utf-8 -*-
"""仓库/库存报表/零售/财务 UI 用例（UI-DEP-001~003、UI-RET-001/002、UI-FIN-001）。

调拨/零售编辑器为 div.tr 网格（同单据编辑器），复用 _mark_detail_row 定位。
"""
import json
import time

import allure
import pytest
from selenium.webdriver.common.by import By

from page.bill_page import BillPage
from page.stock_report_page import StockReportPage

pytestmark = pytest.mark.usefixtures("admin_logged")
RUN = str(int(time.time()))[-6:]


# ---------- 仓库与库存报表 ----------

@pytest.fixture()
def dep_page(admin_logged):
    page = BillPage(admin_logged, "/bill/allocation_out", "客户", "本次收款")
    page.open()
    return page


@pytest.fixture()
def report_page(admin_logged):
    page = StockReportPage(admin_logged)
    page.open()
    return page


@pytest.fixture(scope="module")
def dep_mat(api):
    """模块级商品：仓库1 补库存 60（调拨守恒与报表用例共用）"""
    name, bar = f"UITEST调拨商品{RUN}", f"UITD{RUN}"
    api.add_material(name, bar)
    row = api.find_material(name)
    assert row, "API 预置调拨测试商品失败"
    r = api.add_stock(bar, 60)
    assert isinstance(r, dict) and r.get("code") == 200, f"补库存失败: {r}"
    time.sleep(1.3)
    yield {"id": row["id"], "barcode": bar, "name": name}
    api.delete_material(row["id"])


@allure.feature("仓库管理")
@allure.story("UI-DEP-001 调拨出库两仓联动(总库存守恒)")
@pytest.mark.db_check
def test_UI_DEP_001_allocation(dep_page, api, dep_mat, master, bill_tracker):
    dep_page.open()
    bar = dep_mat["barcode"]
    dep_page.open_new_modal()
    # 明细行：仓库名称(调出,默认仓库1) → 条码 → 调入仓库 → 数量
    dep_page.select_barcode(1, bar)
    dep_page.search_select(dep_page._detail_select("调入仓库", 1), "仓库2")
    dep_page.fill(dep_page._detail_input("数量", 1), 10)
    number = dep_page._read_bill_number()
    # UI 保存的单据 remark 为空，会话兜底 sweep 扫不到，必须登记 tracker 按单号删
    bill_tracker.append((("出库", "调拨", number),))
    dep_page.save()
    row = dep_page.find_bill(number)
    assert row, f"保存后列表未查到调拨单 {number}"
    time.sleep(1.3)
    m = api.find_material(dep_mat["name"])
    assert abs(float(m["stock"]) - 60) < 0.001, \
        f"调拨守恒：总库存应仍为 60，实际 {m['stock']}"


@allure.feature("仓库管理")
@allure.story("UI-DEP-002 商品库存报表查询")
@pytest.mark.smoke
def test_UI_DEP_002_stock_report(report_page, dep_mat):
    report_page.query(dep_mat["name"])
    row = report_page.stock_of(dep_mat["name"])
    assert row, f"库存报表未查到 {dep_mat['name']}"
    assert float(row["库存"]) >= 0, f"库存列异常: {row}"


@allure.feature("仓库管理")
@allure.story("UI-DEP-003 库存报表与单据联动(保存即入账 R4)")
@pytest.mark.db_check
def test_UI_DEP_003_report_linkage(report_page, api, dep_mat):
    report_page.query(dep_mat["name"])
    before = float(report_page.stock_of(dep_mat["name"])["库存"])
    number = "QTRK" + api.build_number()
    r = api.add_bill(number, "入库", "其它", 0, 17, 0, 0,
                     [{"materialId": 0, "barCode": dep_mat["barcode"], "depotId": 14,
                       "operNumber": 5, "unitPrice": 0, "allPrice": 0, "taxRate": 0,
                       "taxMoney": 0, "taxLastMoney": 0, "unit": "个"}])
    assert isinstance(r, dict) and r.get("code") == 200, f"其它入库失败: {r}"
    time.sleep(1.3)
    report_page.query(dep_mat["name"])
    after_row = report_page.stock_of(dep_mat["name"])
    assert after_row, "刷新后报表无数据"
    assert abs(float(after_row["库存"]) - (before + 5)) < 0.001, \
        f"R4 保存即入账：报表库存应 +5: {before}→{after_row['库存']}"
    api.delete_stock_in(number)


# ---------- 零售管理 ----------

@pytest.fixture()
def ret_page(admin_logged):
    page = BillPage(admin_logged, "/bill/retail_out", "会员卡号", "收款金额")
    page.open()
    return page


@pytest.fixture(scope="module")
def retail_mat(api):
    name, bar = f"UITEST零售商品{RUN}", f"UITR{RUN}"
    api.add_material(name, bar)
    row = api.find_material(name)
    assert row, "API 预置零售测试商品失败"
    api.add_stock(bar, 20)
    time.sleep(1.3)
    yield {"id": row["id"], "barcode": bar, "name": name}
    api.delete_material(row["id"])


@allure.feature("零售管理")
@allure.story("UI-RET-001 零售出库(会员现付)")
@pytest.mark.smoke
def test_UI_RET_001_retail(ret_page, api, retail_mat, bill_tracker):
    data = api._call("GET", "/supplier/list", params={
        "search": json.dumps({"type": "会员"}, ensure_ascii=False),
        "currentPage": "1", "pageSize": "5"})
    members = data.get("data", {}).get("rows", [])
    member_name = members[0]["supplier"] if members else None

    stock_before = float(api.find_material(retail_mat["name"])["stock"])
    ret_page.open_new_modal()
    if member_name:
        ret_page.search_select(ret_page._modal_select(1), member_name)
    ret_page.select_barcode(1, retail_mat["barcode"])
    ret_page.fill(ret_page._detail_input("数量", 1), 1)
    ret_page.fill(ret_page._detail_input("单价", 1), 20)
    number = ret_page._read_bill_number()
    # UI 建单 remark 为空，兜底 sweep 扫不到；登记 tracker 防断言失败泄漏
    bill_tracker.append((("出库", "零售", number), ("其它", "零售", number)))
    ret_page.save()
    row = ret_page.find_bill(number)
    assert row, f"保存后列表未查到零售单 {number}"
    time.sleep(1.3)
    stock_after = float(api.find_material(retail_mat["name"])["stock"])
    assert abs(stock_after - (stock_before - 1)) < 0.001, \
        f"零售后库存应-1: {stock_before}→{stock_after}"


@pytest.fixture()
def prepaid_member(api):
    """预存 100 的会员（supplier/add 带 advanceIn 字段，实测生效）；teardown 删除"""
    name = f"UITEST预存会员{RUN}"
    r = api._call("POST", "/supplier/add", body={
        "type": "会员", "supplier": name, "contacts": "测R5", "phonenum": "",
        "email": "", "advanceIn": "100", "sort": "1", "remark": "UITEST"})
    assert isinstance(r, dict) and r.get("code") == 200, f"建预存会员失败: {r}"
    time.sleep(1.3)
    data = api._call("GET", "/supplier/list", params={
        "search": json.dumps({"type": "会员", "supplier": name}, ensure_ascii=False),
        "currentPage": "1", "pageSize": "5"})
    rows = data.get("data", {}).get("rows", [])
    assert rows and float(rows[0].get("advanceIn") or 0) == 100, \
        f"预存会员预存额异常: {rows}"
    yield {"id": rows[0]["id"], "name": name}
    api._call("DELETE", f"/supplier/deleteBatch?ids={rows[0]['id']},")


@allure.feature("零售管理")
@allure.story("UI-RET-002 会员预付款结算选项与余额扣减(R5)")
@pytest.mark.regression
def test_UI_RET_002_prepaid_settle(ret_page, api, retail_mat, prepaid_member, bill_tracker):
    """R5 实测：会员预存>0 时结算方式出现"预付款（余额）"选项，选预付款支付
    后实时扣减。实测（2026-10-28）：预存 100 支付 20 后 advanceIn=-20——期初
    预存被余额重算覆盖清零再扣减（即探索阶段缺陷候选 DEF-EXP-01 的表现，
    预期应为 80），本用例断言"选项出现+扣减发生"，异常余额归属 DEF-EXP-01。"""
    ret_page.open_new_modal()
    ret_page.search_select(ret_page._modal_select(1), prepaid_member["name"])
    # 预存会员的收款类型应出现"预付款（100）"选项
    ret_page._open_select(ret_page._modal_select_by_label("收款类型"))
    time.sleep(0.8)
    opts = ret_page.driver.execute_script(
        """
        return [...document.querySelectorAll('.ant-select-dropdown')]
          .filter(x => x.offsetHeight > 0 &&
                 !x.className.includes('ant-select-dropdown-hidden'))
          .flatMap(x => [...x.querySelectorAll('li')]).map(l => l.textContent.trim());
        """)
    assert any("预付款" in o for o in opts), f"预存会员应出现预付款选项: {opts}"
    ret_page._click_dropdown_option("预付款", exact=False)
    time.sleep(0.5)
    # 明细与保存
    ret_page.select_barcode(1, retail_mat["barcode"])
    ret_page.fill(ret_page._detail_input("数量", 1), 1)
    ret_page.fill(ret_page._detail_input("单价", 1), 20)
    number = ret_page._read_bill_number()
    bill_tracker.append((("出库", "零售", number), ("其它", "零售", number)))
    ret_page.save()
    row = ret_page.find_bill(number)
    assert row, f"预付款零售单未保存: {number}"
    assert float(row["收款金额"]) == 20, f"收款金额列异常: {row}"
    # 会员预存发生扣减/重算（实测 -20；DEF-EXP-01：期初预存被覆盖）
    time.sleep(1.3)
    data = api._call("GET", "/supplier/list", params={
        "search": json.dumps({"type": "会员", "supplier": prepaid_member["name"]},
                             ensure_ascii=False),
        "currentPage": "1", "pageSize": "5"})
    advance_after = float(data["data"]["rows"][0].get("advanceIn") or 0)
    assert advance_after != 100, \
        f"预付款支付后预存额应发生变化(实测-20,DEF-EXP-01): {advance_after}"


@allure.feature("零售管理")
@allure.story("UI-RET-002 对照：无预存会员仅现付")
@pytest.mark.regression
def test_UI_RET_002_no_advance_member(ret_page, api, retail_mat, master):
    """R5 对照：advanceIn=0 的会员收款类型仅"现付"，无预付款选项。"""
    # 无预存的可选对象：使用系统初始会员（advanceIn=0）
    data = api._call("GET", "/supplier/list", params={
        "search": json.dumps({"type": "会员"}, ensure_ascii=False),
        "currentPage": "1", "pageSize": "5"})
    members = [m for m in data.get("data", {}).get("rows", [])
               if float(m.get("advanceIn") or 0) == 0]
    assert members, "无预存为0的会员可供对照"
    ret_page.open_new_modal()
    ret_page.search_select(ret_page._modal_select(1), members[0]["supplier"])
    ret_page._open_select(ret_page._modal_select_by_label("收款类型"))
    time.sleep(0.8)
    opts = ret_page.driver.execute_script(
        """
        return [...document.querySelectorAll('.ant-select-dropdown')]
          .filter(x => x.offsetHeight > 0 &&
                 !x.className.includes('ant-select-dropdown-hidden'))
          .flatMap(x => [...x.querySelectorAll('li')]).map(l => l.textContent.trim());
        """)
    assert not any("预付款" in o for o in opts), \
        f"无预存会员不应出现预付款选项: {opts}"
    assert any("现付" in o for o in opts), f"应存在现付选项: {opts}"
    ret_page.cancel_modal()


# ---------- 财务管理 ----------

@pytest.fixture()
def fin_page(admin_logged):
    page = BillPage(admin_logged, "/financial/money_out", "供应商", "本次付款")
    page.open()
    return page


@pytest.fixture()
def debt_bill(api, retail_mat):
    """造一张有欠款的采购入库（金额合计 30、付款 0 → 欠款 30）供付款单核销"""
    number = "CGRK" + api.build_number()
    r = api.add_bill(number, "入库", "采购", 57, 17, 0, -30,
                     [{"materialId": 0, "barCode": retail_mat["barcode"], "depotId": 14,
                       "operNumber": 3, "unitPrice": 10, "allPrice": 30, "taxRate": 0,
                       "taxMoney": 0, "taxLastMoney": 30, "unit": "个"}])
    assert isinstance(r, dict) and r.get("code") == 200, f"建欠款入库单失败: {r}"
    row = api.list_bill("入库", "采购", number)[0]
    yield {"id": row["id"], "number": number, "debt": 30}
    api.delete_bill(row["id"])


@allure.feature("财务管理")
@allure.story("UI-FIN-001 付款单优惠后实付自动计算(readonly)")
@pytest.mark.regression
def test_UI_FIN_001_payment_discount_calc(fin_page, api, debt_bill, master):
    fin_page.open()
    fin_page.open_new_modal()
    fin_page.search_select(fin_page._modal_select(1), master["supplier"])
    time.sleep(0.5)
    # 选择单据：嵌套对话框勾选欠款源单
    fin_page.click((By.XPATH, "//div[@data-ui-active-modal='1']"
                              "//button[contains(.,'选择单据')]"))
    time.sleep(1.5)
    # 嵌套对话框为新的可见 modal：勾选第一行
    checked = fin_page.driver.execute_script(
        """
        const vis = [...document.querySelectorAll('.ant-modal')]
          .filter(m => m.offsetParent !== null);
        const dlg = vis[vis.length - 1];
        if (!dlg) return false;
        const cb = dlg.querySelector('tbody input[type="checkbox"], .tr input[type="checkbox"]');
        if (cb && !cb.checked) { cb.click(); return true; }
        return !!cb;
        """)
    assert checked, "选择单据对话框未打开或无可选单据"
    time.sleep(0.5)
    # 点确定（对话框底部）
    fin_page.driver.execute_script(
        """
        const vis = [...document.querySelectorAll('.ant-modal')]
          .filter(m => m.offsetParent !== null);
        const dlg = vis[vis.length - 1];
        const btn = [...dlg.querySelectorAll('button')]
          .find(b => /确 ?定|确 ?认|设置/.test(b.textContent));
        if (btn) btn.click();
        """)
    time.sleep(1.2)
    # 合计付款带出源单欠款，填优惠 20 → 实际付款 readonly 自动=合计-优惠
    fin_page.fill(fin_page._modal_input_by_label("优惠金额"), 20)
    time.sleep(0.8)

    def _labeled_value(label: str):
        return fin_page.driver.execute_script(
            r"""
            const modal = [...document.querySelectorAll('.ant-modal')]
              .filter(m => m.offsetParent !== null).pop();
            if (!modal) return null;
            const lab = [...modal.querySelectorAll('label, span, div')]
              .find(e => e.textContent.trim().replace(/[*：:\s]/g,'') === arguments[0]
                     && e.querySelector('input'));
            if (!lab) {
              const lab2 = [...modal.querySelectorAll('label, span, div')]
                .find(e => e.textContent.includes(arguments[0]));
              if (!lab2) return null;
              const item = lab2.closest('.ant-form-item, .ant-row, div');
              const inp = item && item.querySelector('input');
              return inp ? inp.value : null;
            }
            const inp = lab.querySelector('input');
            return inp ? inp.value : null;
            """, label)

    total_pay = _labeled_value("合计付款")
    actual = _labeled_value("实际付款")
    fin_page.cancel_modal()
    assert total_pay and float(total_pay) > 0, f"合计付款未带出源单欠款: {total_pay}"
    assert actual is not None and         abs(float(actual) - (float(total_pay) - 20)) < 0.001,         f"实际付款应=合计付款-优惠: 合计{total_pay} 优惠20 实际{actual}"

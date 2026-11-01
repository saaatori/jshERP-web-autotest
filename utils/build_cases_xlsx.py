# -*- coding: utf-8 -*-
"""生成 data/ui_cases.xlsx（自动化用例登记表）与 data/keywords.xlsx（关键字表）。

与 F:\jsh-ERP-test\03-测试用例\管伊佳ERP-WebUI测试用例.xlsx（59 条全量）的对应关系：
本表只登记"是否自动化=是"的 40 条（不含 19 条手工），执行方式分两类：
- keyword   ：由 Excel 关键字步骤驱动（keywords/executor.py 反射执行）
- codecase  ：复杂链路场景，步骤列为 pytest 节点，由代码用例承载（Excel 登记
              步骤/预期供追溯，驱动入口跳过并记录）
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from utils.config import project_root

HEADERS = ["用例编号", "需求编号", "模块", "用例标题", "优先级", "前置条件",
           "页面/路由", "操作步骤", "预期结果(可见断言)", "执行方式",
           "关键字步骤/节点", "PO对象", "套件标记", "对应测试文件"]

KW = "keyword"
CODE = "codecase"

# (编号, 需求, 模块, 标题, 优先级, 前置, 路由, 步骤, 预期, 方式, 关键字/节点, PO, 套件, 文件)
CASES = [
    ("UI-AUTH-001", "REQ-AUTH-001", "登录认证", "正确账号密码登录进入首页", "P0", "checkcode_flag=0",
     "/user/login", "输入用户名密码→点击登录", "跳转/dashboard；欢迎语出现；左侧10个一级模块",
     KW, "登录|jsh|123456;断言URL|dashboard;断言文本|欢迎您", "LoginPage", "smoke", "excel_driver"),
    ("UI-AUTH-002", "REQ-AUTH-002", "登录认证", "密码错误登录提示", "P0", "jsh账号可用",
     "/user/login", "输入错误密码→登录", "停留登录页；出现错误提示",
     KW, "打开|/user/login;输入|请输入用户名|jsh;输入|请输入密码|wrong_x;点击|登 录;断言URL|user/login",
     "LoginPage", "regression", "excel_driver"),
    ("UI-AUTH-003", "REQ-AUTH-003", "登录认证", "用户名/密码为空前端校验", "P1", "—",
     "/user/login", "空表单点登录", "必填校验提示出现；不发请求",
     KW, "打开|/user/login;点击|登 录;断言文本|请输入用户名",
     "LoginPage", "regression", "excel_driver"),
    ("UI-AUTH-004", "REQ-AUTH-005", "登录认证", "退出登录返回登录页", "P1", "已登录",
     "全局", "点退出登录", "返回/user/login",
     CODE, "testcases/test_login.py::test_UI_AUTH_004_logout", "MenuFrame", "smoke", "test_login"),
    ("UI-AUTH-005", "REQ-AUTH-005", "登录认证", "退出后回退不能进入系统", "P1", "已登录并退出",
     "浏览器回退", "退出→后退", "受保护页面不可见",
     CODE, "testcases/test_login.py::test_UI_AUTH_005_back_after_logout", "LoginPage", "permission", "test_login"),

    ("UI-SYS-001", "REQ-SYS-001", "系统管理", "菜单树完整展示", "P1", "管理员登录",
     "全局", "核对10个一级模块", "10个一级模块齐全",
     CODE, "testcases/test_menu_frame.py::test_UI_SYS_001_menu_tree", "MenuFrame", "smoke", "test_menu_frame"),
    ("UI-SYS-002", "REQ-SYS-001", "系统管理", "多页签打开切换关闭", "P1", "已登录",
     "全局", "开采购入库/销售出库页签→关闭前者", "页签开/关正常",
     CODE, "testcases/test_menu_frame.py::test_UI_SYS_002_tabs", "MenuFrame", "regression", "test_menu_frame"),
    ("UI-SYS-003", "REQ-SYS-001", "系统管理", "受限角色菜单不可见", "P0", "受限角色/用户已建",
     "全局", "受限用户登录核对菜单", "未授权模块不出现（DEF-UI-003/004 实测注记）",
     CODE, "testcases/test_zz_permission.py::test_UI_SYS_003_menu_restricted", "MenuFrame", "permission", "test_permission"),
    ("UI-SYS-004", "REQ-SYS-001", "系统管理", "按钮权限(push_btn)", "P0", "受限角色/用户已建",
     "/material/material", "配置按钮位→核对按钮", "实测按钮位不生效（DEF-UI-005 注记）",
     CODE, "testcases/test_zz_permission.py::test_UI_SYS_004_push_btn_hidden", "MaterialPage", "permission", "test_permission"),
    ("UI-SYS-005", "REQ-SYS-003", "系统管理", "直接输入URL被拦", "P0", "受限用户已登录",
     "地址栏", "直接输入/bill/purchase_in", "不展示业务数据",
     CODE, "testcases/test_zz_permission.py::test_UI_SYS_005_url_blocked", "MenuFrame", "permission", "test_permission"),

    ("UI-GOODS-001", "REQ-GOODS-002", "商品管理", "新增商品成功", "P0", "类别存在",
     "/material/material", "新增→填名称/条码/价格→保存", "列表出现新记录；条码/状态一致",
     CODE, "testcases/test_material.py::test_UI_GOODS_001_new_material", "MaterialPage", "smoke", "test_material"),
    ("UI-GOODS-002", "REQ-GOODS-002", "商品管理", "条码重复保存被拦截", "P1", "存在同条码商品",
     "/material/material", "同条码再保存", "保存被拦；列表不新增（无提示=DEF-UI-001）",
     CODE, "testcases/test_material.py::test_UI_GOODS_002_duplicate_barcode", "MaterialPage", "regression", "test_material"),
    ("UI-GOODS-003", "NFR-USE-001", "商品管理", "必填项为空校验", "P1", "—",
     "/material/material", "名称留空保存", "必填校验出现",
     CODE, "testcases/test_material.py::test_UI_GOODS_003_required_validation", "MaterialPage", "regression", "test_material"),
    ("UI-GOODS-004", "REQ-GOODS-002", "商品管理", "启用/停用切换", "P1", "存在UITEST商品",
     "/material/material", "停用→核对→启用", "状态切换生效",
     CODE, "testcases/test_material.py::test_UI_GOODS_004_enable_disable", "MaterialPage", "regression", "test_material"),

    ("UI-BAS-001", "REQ-BAS-001", "基础资料", "新增供应商成功", "P0", "已登录",
     "/system/vendor", "新增→填写→保存→查询", "列表可查到",
     CODE, "testcases/test_crud.py::test_UI_BAS_001_new_vendor", "VendorPage", "smoke", "test_crud"),
    ("UI-BAS-002", "REQ-BAS-001", "基础资料", "供应商重名提示", "P1", "存在同名",
     "/system/vendor", "重名再保存", "保存被拒且出现提示",
     CODE, "testcases/test_crud.py::test_UI_BAS_002_duplicate_vendor", "VendorPage", "regression", "test_crud"),
    ("UI-BAS-004", "REQ-BAS-001", "基础资料", "新增客户成功", "P1", "已登录",
     "/system/customer", "新增→保存", "列表可见",
     CODE, "testcases/test_crud.py::test_UI_BAS_004_new_customer", "CustomerPage", "regression", "test_crud"),
    ("UI-BAS-005", "REQ-BAS-003", "基础资料", "新增仓库成功", "P1", "已登录",
     "/system/depot", "新增→保存", "列表可见",
     CODE, "testcases/test_crud.py::test_UI_BAS_005_new_depot", "DepotPage", "regression", "test_crud"),

    ("UI-PUR-001", "REQ-PUR-002", "采购管理", "新增采购订单", "P0", "供应商/商品存在",
     "/bill/purchase_order", "新增→选供应商→明细→保存", "CGDD前缀；状态未审核",
     CODE, "testcases/test_purchase.py::test_UI_PUR_001_new_order", "PurchaseOrderPage", "smoke", "test_purchase"),
    ("UI-PUR-002", "REQ-PUR-002", "采购管理", "订单审核状态变化", "P0", "存在未审核订单",
     "/bill/purchase_order", "勾选→审核", "状态列变已审核",
     CODE, "testcases/test_purchase.py::test_UI_PUR_002_audit_order", "PurchaseOrderPage", "smoke", "test_purchase"),
    ("UI-PUR-003", "REQ-PUR-003", "采购管理", "订单转采购入库(部分转)", "P0", "订单已审核",
     "/bill/purchase_order", "勾选→转采购入库→改数量→保存", "源单变部分采购；新CGRK单生成",
     CODE, "testcases/test_purchase.py::test_UI_PUR_003_transfer_partial", "PurchaseOrderPage", "regression", "test_purchase"),
    ("UI-PUR-004", "REQ-PUR-004", "采购管理", "新增采购入库(付款)", "P0", "供应商/商品/账户存在",
     "/bill/purchase_in", "新增→明细→付款20→保存", "金额列与欠款公式(R2)正确",
     CODE, "testcases/test_purchase.py::test_UI_PUR_004_new_purchase_in", "PurchaseInPage", "smoke", "test_purchase"),
    ("UI-PUR-005", "REQ-PUR-007", "采购管理", "列表组合查询与重置", "P1", "存在多张入库单",
     "/bill/purchase_in", "按单号查→无效单号→重置", "过滤正确；重置恢复",
     CODE, "testcases/test_purchase.py::test_UI_PUR_005_query_reset", "PurchaseInPage", "regression", "test_purchase"),
    ("UI-PUR-006", "REQ-PUR-004", "采购管理", "列表金额列与保存值一致", "P1", "存在入库单",
     "/bill/purchase_in", "核对金额5列", "金额合计/含税/付款/欠款一致",
     CODE, "testcases/test_purchase.py::test_UI_PUR_006_amounts", "PurchaseInPage", "db_check", "test_purchase"),
    ("UI-PUR-007", "REQ-PUR-004", "采购管理", "审核入库单(库存不变 R4)", "P1", "存在未审核入库单",
     "/bill/purchase_in", "审核→查库存", "状态已审核；库存不变",
     CODE, "testcases/test_purchase.py::test_UI_PUR_007_audit_purchase_in", "PurchaseInPage", "regression", "test_purchase"),
    ("UI-PUR-008", "REQ-PUR-006", "采购管理", "转采购退货入口", "P1", "存在已审核入库单",
     "/bill/purchase_in", "勾选→转采购退货", "退货编辑器带入原单明细",
     CODE, "testcases/test_purchase.py::test_UI_PUR_008_transfer_back_entry", "PurchaseInPage", "regression", "test_purchase"),

    ("UI-SALE-001", "REQ-SALE-001", "销售管理", "新增销售订单", "P0", "客户/商品存在",
     "/bill/sale_order", "新增→明细→保存", "XSDD前缀；未审核",
     CODE, "testcases/test_sale.py::test_UI_SALE_001_new_order", "SaleOrderPage", "smoke", "test_sale"),
    ("UI-SALE-002", "REQ-SALE-002", "销售管理", "订单转销售出库(部分转)", "P0", "订单已审核",
     "/bill/sale_order", "勾选→转销售出库→改数量→保存", "源单部分执行；新XSCK单",
     CODE, "testcases/test_sale.py::test_UI_SALE_002_transfer_partial", "SaleOrderPage", "regression", "test_sale"),
    ("UI-SALE-003", "REQ-SALE-001", "销售管理", "新增销售出库", "P0", "客户/商品/账户；库存充足",
     "/bill/sale_out", "新增→明细→收款→保存", "金额/欠款(R2)/库存扣减正确",
     CODE, "testcases/test_sale.py::test_UI_SALE_003_new_sale_out", "SaleOutPage", "smoke", "test_sale"),
    ("UI-SALE-004", "REQ-SALE-004", "销售管理", "超库存出库拦截", "P0", "minus_stock_flag=0(测后恢复)",
     "/bill/sale_out", "出库超库存量→保存", "保存被拦；无出库单",
     CODE, "testcases/test_sale.py::test_UI_SALE_004_over_stock_blocked", "SaleOutPage", "regression", "test_sale"),
    ("UI-SALE-005", "REQ-SALE-004", "销售管理", "低于最低售价拦截", "P1", "商品low_decimal=20",
     "/bill/sale_out", "单价15→保存", "保存被拦(8500018)",
     CODE, "testcases/test_sale.py::test_UI_SALE_005_low_price_blocked", "SaleOutPage", "regression", "test_sale"),
    ("UI-SALE-006", "REQ-SALE-003", "销售管理", "仓库权限过滤下拉", "P0", "用户仅授权仓库1",
     "/bill/sale_out", "受限用户新增出库→展开仓库下拉", "授权仓库可选；未授权过滤实测未生效(DEF-UI-002注记)",
     CODE, "testcases/test_zz_permission.py::test_UI_SALE_006_depot_filter", "SaleOutPage", "permission", "test_zz_permission"),
    ("UI-SALE-007", "REQ-SALE-006", "销售管理", "销售退货关联原单", "P1", "存在已审核出库单",
     "/bill/sale_out", "勾选→转销售退货→保存", "库存回补至原值",
     CODE, "testcases/test_sale.py::test_UI_SALE_007_sale_return", "SaleBackPage", "regression", "test_sale"),

    ("UI-DEP-001", "REQ-DEP-002", "仓库管理", "调拨出库两仓联动", "P1", "两仓有库存",
     "/bill/allocation_out", "调拨10个→保存", "总库存守恒",
     CODE, "testcases/test_dep_ret_fin.py::test_UI_DEP_001_allocation", "AllocationPage", "db_check", "test_dep_ret_fin"),
    ("UI-DEP-002", "REQ-DEP-004", "仓库管理", "商品库存报表查询", "P1", "存在库存",
     "/report/material_stock", "按商品筛选", "库存列正确",
     CODE, "testcases/test_dep_ret_fin.py::test_UI_DEP_002_stock_report", "StockReportPage", "smoke", "test_dep_ret_fin"),
    ("UI-DEP-003", "REQ-DEP-004", "仓库管理", "库存报表与单据联动", "P1", "库存已知",
     "/report/material_stock", "其它入库+5→刷新", "报表库存+5(保存即入账R4)",
     CODE, "testcases/test_dep_ret_fin.py::test_UI_DEP_003_report_linkage", "StockReportPage", "db_check", "test_dep_ret_fin"),

    ("UI-RET-001", "REQ-RET-001", "零售管理", "零售出库(会员现付)", "P1", "会员/商品/账户存在",
     "/bill/retail_out", "新增→会员→明细→保存", "库存-1；LSCK单生成",
     CODE, "testcases/test_dep_ret_fin.py::test_UI_RET_001_retail", "RetailOutPage", "smoke", "test_dep_ret_fin"),

    ("UI-RET-002", "REQ-RET-001", "零售管理", "会员预付款结算选项与余额扣减(R5)", "P1", "会员预存>0(API建)",
     "/bill/retail_out", "选预存会员→收款类型选预付款→明细→保存", "预付款(100)选项出现；保存成功；预存额扣减(实测-20=DEF-EXP-01注记)",
     CODE, "testcases/test_dep_ret_fin.py::test_UI_RET_002_prepaid_settle", "RetailOutPage", "regression", "test_dep_ret_fin"),
    ("UI-RET-002C", "REQ-RET-001", "零售管理", "对照：无预存会员仅现付", "P1", "存在advanceIn=0会员",
     "/bill/retail_out", "选无预存会员→展开收款类型", "仅现付无预付款选项",
     CODE, "testcases/test_dep_ret_fin.py::test_UI_RET_002_no_advance_member", "RetailOutPage", "regression", "test_dep_ret_fin"),
    ("UI-FIN-001", "REQ-FIN-003", "财务管理", "付款单优惠实付自动计算", "P1", "供应商存在欠款",
     "/financial/money_out", "选择单据→优惠20", "实际付款=合计-优惠(readonly)",
     CODE, "testcases/test_dep_ret_fin.py::test_UI_FIN_001_payment_discount_calc", "MoneyOutPage", "regression", "test_dep_ret_fin"),

    ("UI-COM-001", "NFR-USE-002", "通用交互", "弹窗确认与取消行为", "P1", "存在可删除数据(API建)",
     "/system/vendor", "删除→确认；删除→取消", "确认执行删除；取消不执行且行保留",
     CODE, "testcases/test_common.py::test_UI_COM_001_confirm_cancel", "BasePage", "regression", "test_common"),
]

KEYWORDS = [
    ("打开", "打开指定路由页面并清理浮层", "路由，如 /user/login"),
    ("登录", "使用指定账号登录（默认管理员）", "用户名,密码"),
    ("退出", "点击右上角退出登录", "—"),
    ("输入", "向 placeholder 匹配的输入框输入文本", "placeholder,文本"),
    ("点击", "点击按钮/链接（按文本匹配）", "按钮文本"),
    ("等待", "固定等待秒数", "秒"),
    ("断言URL", "断言当前URL包含指定片段", "URL片段"),
    ("断言文本", "断言页面出现指定文本", "文本"),
    ("断言消息", "断言 antd message 提示包含指定文本", "文本片段"),
    ("断言行", "断言列表存在指定行", "路由,行文本"),
    ("截图", "保存截图到 reports/screenshots", "名称"),
]


def _sheet(wb, title, headers, rows, widths):
    ws = wb.create_sheet(title)
    head_fill = PatternFill("solid", fgColor="2F5597")
    for c, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=c, value=h)
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = head_fill
        cell.alignment = Alignment(horizontal="center")
        ws.column_dimensions[cell.column_letter].width = widths[c - 1]
    for r, row in enumerate(rows, 2):
        for c, v in enumerate(row, 1):
            ws.cell(row=r, column=c, value=v)
    ws.freeze_panes = "A2"
    return ws


def main():
    out_dir = os.path.join(project_root(), "data")
    os.makedirs(out_dir, exist_ok=True)

    wb = Workbook()
    wb.remove(wb.active)
    _sheet(wb, "ui_cases",
           HEADERS,
           [list(c) for c in CASES],
           [14, 14, 10, 24, 6, 18, 20, 30, 32, 9, 40, 16, 10, 18])
    wb.save(os.path.join(out_dir, "ui_cases.xlsx"))

    wb2 = Workbook()
    wb2.remove(wb2.active)
    _sheet(wb2, "keywords",
           ["关键字", "说明", "参数"],
           [list(k) for k in KEYWORDS],
           [12, 40, 24])
    wb2.save(os.path.join(out_dir, "keywords.xlsx"))
    print(f"已生成 ui_cases.xlsx（{len(CASES)}条）与 keywords.xlsx（{len(KEYWORDS)}个关键字）")


if __name__ == "__main__":
    main()

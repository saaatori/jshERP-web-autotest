# -*- coding: utf-8 -*-
"""数据准备/清理的后门通道（计划 §3.3 第5条：测试数据通过接口或 SQL 预置）。

约定沿用项目一《validate_smoke.py》实测结论：
- 登录 POST /user/login，password 为 32 位小写 MD5；
- 请求头 X-Access-Token；
- 业务失败时 HTTP 200 + code!=200，断言落到 msgTip/业务字段；
- 同一秒内第二次操作会触发防攻击强制注销（缺陷 DEF-EXP-06），
  所有请求强制间隔 >=1.2s。
"""
import hashlib
import json
import time
from typing import Any, Optional

import requests

from utils.logger import get_logger

log = get_logger(__name__)

MIN_INTERVAL = 1.2  # DEF-EXP-06：同用户同模块同 IP 同一秒第二次操作会被强制注销


class JshApi:
    def __init__(self, api_base: str, login_name: str, password: str):
        self.base = api_base.rstrip("/")
        self.login_name = login_name
        self.password = password
        self.token: Optional[str] = None
        self._last_call = 0.0

    # ---- 基础 ----
    def _throttle(self) -> None:
        gap = time.time() - self._last_call
        if gap < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - gap)
        self._last_call = time.time()

    def _call(self, method: str, path: str, params=None, body=None) -> Any:
        resp_data = self._call_raw(method, path, params, body)
        # loginOut = 会话被防攻击机制强制注销（DEF-EXP-06）或过期：重登一次再试
        if isinstance(resp_data, str) and "loginOut" in resp_data and self.token:
            log.warning("会话失效(loginOut)，自动重新登录后重试: %s", path)
            self.token = None
            self.login()
            resp_data = self._call_raw(method, path, params, body)
        return resp_data

    def _call_raw(self, method: str, path: str, params=None, body=None) -> Any:
        self._throttle()
        url = self.base + path
        headers = {"X-Access-Token": self.token} if self.token else {}
        resp = requests.request(method, url, params=params, json=body,
                                headers=headers, timeout=15)
        log.info("%s %s -> %s", method, path, resp.status_code)
        try:
            return resp.json()
        except ValueError:
            return resp.text

    def login(self) -> str:
        md5 = hashlib.md5(self.password.encode()).hexdigest()
        data = self._call("POST", "/user/login",
                          body={"loginName": self.login_name, "password": md5})
        self.token = data["data"]["token"]
        return self.token

    # ---- 商品 ----
    def add_material(self, name: str, barcode: str, purchase="10", sale="20",
                     low="20", unit="个") -> Any:
        return self._call("POST", "/material/add", body={
            "name": name, "unit": unit, "mnemonic": "UIT",
            "meList": [{"id": "", "barCode": barcode, "commodityUnit": unit,
                        "sku": "", "purchaseDecimal": purchase,
                        "commodityDecimal": sale, "wholesaleDecimal": "",
                        "lowDecimal": low}],
            "stock": [], "sortList": [], "unitId": "", "imgName": "",
            "meDeleteIdList": [],
        })

    def find_material(self, keyword: str) -> Optional[dict]:
        data = self._call("GET", "/material/list", params={
            "search": json.dumps({"materialParam": keyword}, ensure_ascii=False),
            "currentPage": "1", "pageSize": "10"})
        rows = data["data"]["rows"] if isinstance(data, dict) else []
        return rows[0] if rows else None

    def delete_material(self, material_id) -> Any:
        # 实测：开源版 V3.6 (commit 8f5dc08) 路径为 /material/deleteBatch
        return self._call("DELETE", f"/material/deleteBatch?ids={material_id},")

    # ---- 单据 ----
    def build_number(self) -> str:
        data = self._call("GET", "/sequence/buildNumber")
        return data["data"]["defaultNumber"]

    def add_bill(self, number: str, bill_type: str, sub_type: str, organ_id: int,
                 account_id: int, change_amount: float, total_price: float,
                 rows: list, remark="UITEST") -> Any:
        info = {"operTime": time.strftime("%Y-%m-%d %H:%M:%S"), "number": number,
                "type": bill_type, "subType": sub_type, "organId": organ_id,
                "accountId": account_id, "changeAmount": change_amount,
                "discountLastMoney": abs(total_price), "totalPrice": total_price,
                "status": "0", "remark": remark}
        return self._call("POST", "/depotHead/addDepotHeadAndDetail", body={
            "info": json.dumps(info, ensure_ascii=False),
            "rows": json.dumps(rows, ensure_ascii=False)})

    def list_bill(self, bill_type: str, sub_type: str, number: str) -> list:
        data = self._call("GET", "/depotHead/list", params={
            "search": json.dumps({"type": bill_type, "subType": sub_type,
                                  "number": number}, ensure_ascii=False),
            "currentPage": "1", "pageSize": "10"})
        return data["data"]["rows"] if isinstance(data, dict) else []

    def delete_bill(self, bill_id) -> Any:
        return self._call("DELETE", f"/depotHead/deleteBatch?ids={bill_id},")

    def set_bill_status(self, bill_id, status: str) -> Any:
        """审核(1)/反审核(0)：POST /depotHead/batchSetStatus，JSON body 实测有效。
        响应可能为非 JSON 文本（如 loginOut，防攻击误杀），容错处理。"""
        import requests as _rq
        self._throttle()
        resp = _rq.post(f"{self.base}/depotHead/batchSetStatus",
                        json={"ids": str(bill_id), "status": str(status)},
                        headers={"X-Access-Token": self.token}, timeout=15)
        self._last_call = time.time()
        try:
            return resp.json()
        except ValueError:
            return resp.text

    def safe_delete_bill(self, bill_id) -> None:
        """teardown 用：反审核→删除（已审核单禁删 8500011，见探索发现 F6）"""
        self.set_bill_status(bill_id, "0")
        self.delete_bill(bill_id)

    def audit_bill(self, bill_id) -> Any:
        return self._call("POST", f"/depotHead/batchAudit?ids={bill_id}&status=1")

    # ---- 主数据（动态解析名称，避免硬编码 ID）----
    def _pick(self, items: list, key: str, preferred: str) -> str:
        """优先取规范名，规避探索期残留的 EXPF* 等测试数据"""
        for it in items:
            if str(it.get(key)) == preferred:
                return preferred
        return str(items[0][key])

    def master_data(self) -> dict:
        sup = self._call("GET", "/supplier/list", params={
            "search": json.dumps({"type": "供应商"}, ensure_ascii=False),
            "currentPage": "1", "pageSize": "50"})
        time.sleep(0.1)
        cus = self._call("GET", "/supplier/list", params={
            "search": json.dumps({"type": "客户"}, ensure_ascii=False),
            "currentPage": "1", "pageSize": "50"})
        time.sleep(0.1)
        dep = self._call("GET", "/depot/list")
        time.sleep(0.1)
        acc = self._call("GET", "/account/list", params={
            "search": "", "currentPage": "1", "pageSize": "50"})
        return {
            "supplier": self._pick(sup["data"]["rows"], "supplier", "供应商1"),
            "customer": self._pick(cus["data"]["rows"], "supplier", "客户1"),
            "depot": self._pick(dep["data"]["rows"], "name", "仓库1"),
            "account": self._pick(acc["data"]["rows"], "name", "账户1"),
        }

    def add_stock(self, barcode: str, qty, depot_id: int = 14) -> Any:
        """其它入库补库存（type='入库'/subType='其它'，实测口径；删除单据自动回退）"""
        number = "QTRK" + self.build_number()
        return self.add_bill(number, "入库", "其它", 0, 17, 0, 0,
                             [{"materialId": 0, "barCode": barcode, "depotId": depot_id,
                               "operNumber": qty, "unitPrice": 0, "allPrice": 0,
                               "taxRate": 0, "taxMoney": 0, "taxLastMoney": 0,
                               "unit": "个"}], remark="UITEST补库存")

    def delete_stock_in(self, number: str) -> None:
        rows = self.list_bill("入库", "其它", number)
        if rows:
            self.delete_bill(rows[0]["id"])

    # ---- 角色按钮位（UI-SYS-004 用；btnStr 非空会使非经理用户菜单接口 500，
    #      见 DEF-UI-004，测后必须清除）----
    def find_role_id(self, name: str) -> Optional[int]:
        """按名称查角色 id（/role/allList 裸数组）；不存在返回 None。
        权限用例经此动态获取受限角色 id（bootstrap 脚本创建「UITEST受限」），
        不再硬编码库内自增 id。"""
        data = self._call("GET", "/role/allList")
        for row in data if isinstance(data, list) else []:
            if str(row.get("name")) == name:
                return row["id"]
        return None

    def set_role_btn_str(self, role_id, btn_str) -> None:
        """写角色按钮位（UI-SYS-004）。注意：btn_str 传 None 后端会忽略
        （实测清理无效、字段保持原值），内部统一转空串实现真正清除。"""
        btn_str = btn_str or ""
        r = self._call("GET", "/userBusiness/getBasicData",
                       params={"Type": "RoleFunctions", "KeyId": str(role_id)})
        lst = r.get("data", {}).get("userBusinessList", [])
        assert lst, f"角色 {role_id} 无 RoleFunctions 记录"
        rec = lst[0]
        value = rec["value"]
        ids = [int(x) for x in value.replace("[", "").split("]") if x.strip()]
        self._call("PUT", "/userBusiness/update",
                   body={"type": "RoleFunctions", "keyId": int(role_id),
                         "value": ids, "id": rec["id"], "btnStr": btn_str})

    # ---- 系统开关（minus_stock_flag 翻转，UI-SALE-004 用；测后必须恢复）----
    def get_system_config(self) -> dict:
        data = self._call("GET", "/systemConfig/getCurrentInfo")
        return data["data"]

    def set_minus_stock_flag(self, value: str) -> None:
        info = self.get_system_config()
        info["minusStockFlag"] = str(value)
        self._call("PUT", "/systemConfig/update", body=info)

    def sweep_test_data(self) -> dict:
        """会话结束兜底清理：按 UITEST 前缀扫删本框架产生的测试数据
        （单据[remark=UITEST*] → 往来单位 → 仓库 → 结算账户 → 商品）。
        不触碰测试账号体系（用户/角色/绑定）与系统原生数据。
        已知不覆盖：财务单据（accountHead，当前无用例保存此类单据）。"""
        removed = {"bill": 0, "supplier": 0, "depot": 0, "account": 0, "material": 0}
        for t, st in (("其它", "采购订单"), ("订单", "采购订单"), ("其它", "销售订单"),
                      ("订单", "销售订单"), ("入库", "其它"), ("入库", "采购"),
                      ("出库", "销售"), ("入库", "销售退货"), ("出库", "调拨"),
                      ("出库", "零售")):
            d = self._call("GET", "/depotHead/list", params={
                "search": json.dumps({"type": t, "subType": st, "number": ""},
                                     ensure_ascii=False),
                "currentPage": "1", "pageSize": "50"})
            if not isinstance(d, dict):
                continue
            for r in (d.get("data") or {}).get("rows", []) or []:
                if str(r.get("remark") or "").startswith("UITEST"):
                    self.delete_bill(r["id"])
                    removed["bill"] += 1
        for t in ("供应商", "客户", "会员"):
            d = self._call("GET", "/supplier/list", params={
                "search": json.dumps({"type": t}, ensure_ascii=False),
                "currentPage": "1", "pageSize": "50"})
            if not isinstance(d, dict):
                continue
            for r in (d.get("data") or {}).get("rows", []) or []:
                if str(r.get("supplier") or "").startswith("UITEST"):
                    self._call("DELETE", f"/supplier/deleteBatch?ids={r['id']},")
                    removed["supplier"] += 1
        d = self._call("GET", "/depot/list")
        if isinstance(d, dict):
            for r in (d.get("data") or {}).get("rows", []) or []:
                if str(r.get("name") or "").startswith("UITEST"):
                    self._call("DELETE", f"/depot/deleteBatch?ids={r['id']},")
                    removed["depot"] += 1
        d = self._call("GET", "/account/list", params={
            "search": "", "currentPage": "1", "pageSize": "50"})
        if isinstance(d, dict):
            for r in (d.get("data") or {}).get("rows", []) or []:
                if str(r.get("name") or "").startswith("UITEST"):
                    self._call("DELETE", f"/account/deleteBatch?ids={r['id']},")
                    removed["account"] += 1
        for _ in range(10):  # 删一页再查一页，直到清空（防长尾分页）
            d = self._call("GET", "/material/list", params={
                "search": json.dumps({"materialParam": "UITEST"}, ensure_ascii=False),
                "currentPage": "1", "pageSize": "50"})
            if not isinstance(d, dict):
                break
            rows = (d.get("data") or {}).get("rows", []) or []
            if not rows:
                break
            for r in rows:
                if str(r.get("name") or "").startswith("UITEST"):
                    self.delete_material(r["id"])
                    removed["material"] += 1
        return removed

    def close(self) -> None:
        """teardown 备用：退出会话，避免 token 悬挂"""
        if self.token:
            try:
                self._call("POST", "/user/logout")
            except Exception:  # noqa: BLE001 - 清理尽力而为
                pass

# -*- coding: utf-8 -*-
r"""测试账号基础设施一键重建（幂等）。

背景：数据库重置会清空调试期手工创建的测试账号，而 conftest 的 api 夹具与
权限用例硬依赖它们。本脚本走接口通道按当前库动态发现 id，一条命令恢复：

    python utils/bootstrap_test_accounts.py

创建内容（已存在则跳过）：
- 角色「UITEST管理员」：绑定全部功能菜单
- 角色「UITEST受限」：仅 商品信息 + 销售管理 + 销售出库（UI-SYS-003/004/005 用）
- 用户 uitest_api/123456：ismanager=1，绑「UITEST管理员」（conftest api 夹具用）
- 用户 uitest_ro/123456：ismanager=0，绑「UITEST受限」+ 仓库授权=仓库1
- 用户 uitest_sale/123456：ismanager=0，绑「销售代表」+ 仓库授权=仓库1（UI-SALE-006 用）

所有 id（角色/用户/功能/仓库）均动态发现，不依赖旧库硬编码值；
权限用例通过 api.find_role_id("UITEST受限") 获取角色 id，不再写死 56。
"""
import hashlib
import json
import sys
import time

sys.path.insert(0, ".")

from utils.api_helper import JshApi
from utils.config import load_config

PASSWORD = "123456"
ADMIN_ROLE = "UITEST管理员"
RO_ROLE = "UITEST受限"
SALE_ROLE = "销售代表"  # 系统原生角色，重置后仍在

RO_FUNCTIONS = ["商品信息", "销售管理", "销售出库"]  # 按名称发现功能 id


def _md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()


def _fetch_functions(api: JshApi) -> dict:
    """POST /function/findMenuByPNumber 拉功能树（必须带 body，裸调 500），
    返回 {名称: id}（含父级模块）。"""
    import requests
    cfg = load_config()
    r = requests.post(cfg["api_base_url"] + "/function/findMenuByPNumber",
                      json={"pNumber": 0, "userId": _admin_uid(api)},
                      headers={"X-Access-Token": api.token}, timeout=15)
    tree = r.json()
    if isinstance(tree, dict):
        tree = tree.get("data") or []
    funcs = {}

    def walk(items):
        for it in items:
            fid, name = it.get("id"), (it.get("text") or "").strip()
            if fid and name:
                funcs.setdefault(name, fid)
            walk(it.get("children") or [])

    walk(tree)
    return funcs


def _admin_uid(api: JshApi) -> int:
    data = api._call("GET", "/user/getUserList", params={
        "search": json.dumps({}), "currentPage": "1", "pageSize": "20"})
    for row in data if isinstance(data, list) else []:
        if "测试用户" in str(row.get("userName") or row.get("username")):
            return row["id"]
    raise AssertionError("未找到管理员账号（getUserList 无 测试用户）")


def find_user_id(api: JshApi, user_name: str):
    """按显示名查用户 id（getUserList 裸数组，显示名字段大小写两版兼容）；
    不存在返回 None"""
    data = api._call("GET", "/user/getUserList", params={
        "search": json.dumps({}), "currentPage": "1", "pageSize": "50"})
    for row in data if isinstance(data, list) else []:
        display = str(row.get("userName") or row.get("username") or "")
        if display == user_name:
            return row["id"]
    return None


def ensure_role(api: JshApi, name: str, function_ids=None) -> int:
    """角色不存在则创建并绑定功能（userBusiness/RoleFunctions），返回角色 id"""
    role_id = api.find_role_id(name)
    if role_id is None:
        r = api._call("POST", "/role/add", body={"name": name, "priceLimit": ""})
        assert isinstance(r, dict) and r.get("code") == 200, f"建角色 {name} 失败: {r}"
        time.sleep(1.3)
        role_id = api.find_role_id(name)
        assert role_id, f"角色 {name} 建后查询不到"
        print(f"  角色 [{name}] 已创建 id={role_id}")
    else:
        print(f"  角色 [{name}] 已存在 id={role_id}")
    if function_ids is not None:
        _ensure_binding(api, "RoleFunctions", role_id, function_ids)
    return role_id


def _get_binding_value(api: JshApi, btype: str, key_id: int):
    r = api._call("GET", "/userBusiness/getBasicData",
                  params={"Type": btype, "KeyId": str(key_id)})
    lst = (r.get("data") or {}).get("userBusinessList") or []
    if not lst:
        return None, None
    rec = lst[0]
    value = rec.get("value")
    if isinstance(value, str):
        ids = [int(x) for x in value.replace("[", "").split("]") if x.strip()]
    else:
        ids = [int(x) for x in (value or [])]
    return rec.get("id"), ids


def _ensure_binding(api: JshApi, btype: str, key_id: int, ids: list) -> None:
    """幂等绑定：已存在且值一致则跳过，否则 update / 不存在则 add。
    值格式与文档 4.1 实测口径一致（update 用数字数组）。"""
    rec_id, old_ids = _get_binding_value(api, btype, key_id)
    if old_ids == [int(x) for x in ids]:
        print(f"    绑定 {btype} keyId={key_id} 已是目标值 {ids}")
        return
    body = {"type": btype, "keyId": int(key_id), "value": [int(x) for x in ids]}
    if rec_id is not None:
        body["id"] = rec_id
        r = api._call("PUT", "/userBusiness/update", body=body)
    else:
        r = api._call("POST", "/userBusiness/add", body=body)
    assert isinstance(r, dict) and r.get("code") == 200, \
        f"绑定 {btype} keyId={key_id} 失败: {r}"
    time.sleep(1.3)
    _, now_ids = _get_binding_value(api, btype, key_id)
    assert now_ids == [int(x) for x in ids], \
        f"绑定回读不一致: 期望 {ids} 实际 {now_ids}"
    print(f"    绑定 {btype} keyId={key_id} -> {ids}")


def ensure_user(api: JshApi, login_name: str, user_name: str, ismanager: int,
                role_id: int, depot_id: int = None) -> int:
    """用户不存在则创建（密码 MD5 入库，与登录口径一致），绑角色；可选绑仓库"""
    uid = find_user_id(api, user_name)
    if uid is None:
        r = api._call("POST", "/user/add", body={
            "loginName": login_name, "username": user_name,
            "password": _md5(PASSWORD), "ismanager": str(ismanager),
            "phonenum": "", "email": "", "description": "自动化测试基础设施"})
        assert isinstance(r, dict) and r.get("code") == 200, \
            f"建用户 {login_name} 失败: {r}"
        time.sleep(1.3)
        uid = find_user_id(api, user_name)
        assert uid, f"用户 {login_name} 建后查询不到"
        print(f"  用户 [{login_name}] 已创建 id={uid}")
    else:
        print(f"  用户 [{login_name}] 已存在 id={uid}")
    _ensure_binding(api, "UserRole", uid, [role_id])
    if depot_id is not None:
        _ensure_binding(api, "Warehouse", uid, [depot_id])
    return uid


def verify_login(cfg: dict, login_name: str) -> None:
    client = JshApi(cfg["api_base_url"], login_name, PASSWORD)
    client.login()
    print(f"  登录验证 {login_name} OK")


def main():
    cfg = load_config()
    acct = cfg["account"]["admin"]
    api = JshApi(cfg["api_base_url"], acct["login_name"], acct["password"])
    api.login()

    print("== 1. 功能清单 ==")
    funcs = _fetch_functions(api)
    missing = [n for n in RO_FUNCTIONS if n not in funcs]
    assert not missing, f"功能树缺少 {missing}，现有: {list(funcs)}"
    all_ids = sorted(set(funcs.values()))
    print(f"  功能 {len(funcs)} 项；受限功能 id: "
          f"{[(n, funcs[n]) for n in RO_FUNCTIONS]}")

    print("== 2. 角色 ==")
    admin_role = ensure_role(api, ADMIN_ROLE, all_ids)
    ro_role = ensure_role(api, RO_ROLE, [funcs[n] for n in RO_FUNCTIONS])
    sale_role = api.find_role_id(SALE_ROLE)
    assert sale_role, f"原生角色 {SALE_ROLE} 不存在，请先确认库初始化"
    print(f"  原生角色 [{SALE_ROLE}] id={sale_role}")

    print("== 3. 用户 ==")
    depot_id = _depot1_id(api)
    ensure_user(api, "uitest_api", "UITEST接口账号", 1, admin_role)
    ensure_user(api, "uitest_ro", "UITEST只读用户", 0, ro_role, depot_id)
    ensure_user(api, "uitest_sale", "UITEST销售用户", 0, sale_role, depot_id)

    print("== 4. 登录验证 ==")
    for login_name in ("uitest_api", "uitest_ro", "uitest_sale"):
        verify_login(cfg, login_name)

    print("完成。受限角色 id =", ro_role, "（权限用例经 api.find_role_id 动态获取）")


def _depot1_id(api: JshApi) -> int:
    d = api._call("GET", "/depot/list")
    for row in (d.get("data") or {}).get("rows", []) or []:
        if str(row.get("name")) == "仓库1":
            return row["id"]
    raise AssertionError("仓库1 不存在，请确认基础资料初始化")


if __name__ == "__main__":
    main()

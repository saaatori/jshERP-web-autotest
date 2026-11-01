# -*- coding: utf-8 -*-
"""Excel 读写：用例表（ui_cases.xlsx）与关键字表（keywords.xlsx）"""
from typing import List

from openpyxl import load_workbook


def read_sheet(path: str, sheet: str | None = None, header_row: int = 4) -> List[dict]:
    """按表头行读取为字典列表；空行（用例编号为空）自动跳过"""
    wb = load_workbook(path, data_only=True)
    ws = wb[sheet] if sheet else wb.active
    rows = list(ws.iter_rows(values_only=True))
    headers = [str(h).strip() if h is not None else f"col{i}" for i, h in enumerate(rows[header_row - 1])]
    cases = []
    for row in rows[header_row:]:
        if row is None or all(v is None or str(v).strip() == "" for v in row):
            continue
        case = {}
        for i, h in enumerate(headers):
            case[h] = "" if i >= len(row) or row[i] is None else str(row[i]).strip()
        if case.get(headers[0], ""):
            cases.append(case)
    wb.close()
    return cases

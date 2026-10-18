"""工具型评测的判分：读取工作目录中的 answer.json / 输出 CSV 与标准答案比对"""

import json
import re
from pathlib import Path

import pandas as pd

EXP = Path(__file__).parent / "expected"


def tol_of(question):
    m = re.search(r"保留(\d)位小数", question)
    return (10 ** -int(m.group(1)) if m else 0) + 1e-9


def to_num(x):
    if isinstance(x, bool):
        return None
    if isinstance(x, (int, float)):
        return float(x)
    try:
        return float(str(x).strip().replace(",", ""))
    except ValueError:
        return None


def norm(s):
    return str(s).strip().strip("\"'").lower()


def same(exp, got, tol):
    if isinstance(exp, (int, float)) and not isinstance(exp, bool):
        g = to_num(got)
        return g is not None and abs(g - exp) <= tol
    return norm(exp) == norm(got)


def short(x, n=120):
    s = json.dumps(x, ensure_ascii=False) if not isinstance(x, str) else x
    return s if len(s) <= n else s[:n] + "…"


def cmp_csv(exp_file, got_file, keys, num_tol):
    e = pd.read_csv(exp_file, dtype=str, keep_default_na=False)
    try:
        g = pd.read_csv(got_file, dtype=str, keep_default_na=False, encoding="utf-8-sig")
    except Exception as ex:  # noqa: BLE001
        return False, f"读取失败: {ex}"
    g.columns = [c.strip() for c in g.columns]
    if list(g.columns) != list(e.columns):
        return False, f"列不一致: {list(g.columns)}"
    if len(g) != len(e):
        return False, f"行数 {len(g)} ≠ {len(e)}"
    e = e.sort_values(keys).reset_index(drop=True)
    g = g.assign(**{k: g[k].str.strip() for k in keys}).sort_values(keys).reset_index(drop=True)
    for col in e.columns:
        if col in num_tol:
            for i, (a, b) in enumerate(zip(e[col], g[col])):
                if (a.strip() == "") != (b.strip() == ""):
                    return False, f"{col} 第{i}行 空值不一致"
                if a.strip() and not same(float(a), b, num_tol[col]):
                    return False, f"{col} 第{i}行 期望 {a} 实际 {b}"
        else:
            bad = (e[col].str.strip() != g[col].str.strip())
            if bad.any():
                i = int(bad.idxmax())
                return False, f"{col} 第{i}行 期望 {e[col][i]!r} 实际 {g[col][i]!r}（共 {int(bad.sum())} 处）"
    return True, "ok"


def score(case, workdir):
    """返回 (correct, parsed, reason)"""
    workdir = Path(workdir)
    ans_path = workdir / "answer.json"
    if not ans_path.exists():
        return False, None, "缺少 answer.json"
    try:
        obj = json.loads(ans_path.read_text(encoding="utf-8-sig"))
    except Exception as ex:  # noqa: BLE001
        return False, None, f"answer.json 解析失败: {ex}"
    ans = obj.get("answer", obj) if isinstance(obj, dict) else obj
    exp, t, tol = case["expected"], case["answer_type"], tol_of(case["question"])

    if t == "csv":
        f = workdir / exp
        if not f.exists():
            return False, short(ans), f"缺少输出文件 {exp}"
        ok, why = cmp_csv(EXP / f"{case['id']:03d}_{exp}", f, case["key_cols"], case["num_tol"])
        return ok, exp, why
    if t in ("integer", "number", "string"):
        ok = same(exp, ans, 1e-9 if t == "integer" else tol)
        return ok, short(ans), "ok" if ok else "答案不符"
    if t == "list":
        if not isinstance(ans, list):
            return False, short(ans), "不是数组"
        ok = len(ans) == len(exp) and all(same(a, b, tol) for a, b in zip(exp, ans))
        return ok, short(ans), "ok" if ok else "数组不符"
    if t == "dict":
        if not isinstance(ans, dict):
            return False, short(ans), "不是对象"
        g = {norm(k): v for k, v in ans.items()}
        e = {norm(k): v for k, v in exp.items()}
        ok = g.keys() == e.keys() and all(same(e[k], g[k], tol) for k in e)
        return ok, short(ans), "ok" if ok else "对象不符"
    raise ValueError(t)

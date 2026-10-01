#!/usr/bin/env python3
"""probe.py —— "作弊者"的读题器。

复现真实参赛队（代号 FEVER）被申诉复核确认的做法：
  1. find_tests_dir()        ~ 其 verify/verify.py:672-716  _find_tests_dir()        (PDF 第 1-2 页)
  2. test_flow_clauses()     ~ 其 verify/verify.py:719-777  _test_flow_clauses()     (PDF 第 2-3 页)
  3. official_query_shapes() ~ 其 verify/verify.py:847-932  _official_query_shapes() (PDF 第 2-3 页)
输出字段与 FEVER 自检报告 report["level2"] 对齐：
  test_flow_source / test_flow_clauses / query_shapes (PDF 第 3 页)

用法：python3 probe.py
  - 若评测测试被"挂载"在候选路径（见下），输出偷到的契约情报；
  - 若没有挂载，输出 test_flow_source: null —— 这正是 FEVER 自述在平台 gate 上的现象。
注意：probe.py 故意【不】直接读本仓库的 test-package/tests，
     只读"平台挂载点"，这样才能真实演示"挂载=开卷，不挂载=两眼一抹黑"。
"""
import json, os, re, sys
from pathlib import Path

REPO = Path(__file__).resolve().parent

def find_tests_dir() -> Path | None:
    """第 1 步：探测正式测试目录。FEVER 的候选与识别条件见 PDF 第 2 页复核原文。"""
    candidates = []
    for key in ("ARC_TESTS_DIR", "ARCBENCH_TESTS_DIR", "ARC_EXPORT_DIR"):
        v = os.environ.get(key, "")
        if v:
            candidates += [Path(v), Path(v) / "staging" / "tests-context"]
    candidates += [
        Path("/workspace/tests"),                       # 线上平台的挂载点（PDF 第 2 页）
        REPO / "_demo" / "workspace" / "tests",         # 本仓库用 run.sh 模拟的挂载点
        REPO / "_demo" / "workspace" / "staging" / "tests-context",
    ]
    for base in candidates:
        if base.is_dir() and any(base.glob("*.spec.ts")):
            return base  # FEVER 还要求同时存在 helpers.ts；本测试包的等价物是 support/e2e.ts
    return None

ROLE_RE  = re.compile(r"getByRole\('(\w+)',\s*\{\s*name:\s*'([^']+)'(?:,\s*exact:\s*(true))?", re.S)
LABEL_RE = re.compile(r"getByLabel\('([^']+)'\)")
TEXT_RE  = re.compile(r"getByText\('([^']+)'(?:,\s*\{\s*exact:\s*(true))?", re.S)
TEST_RE  = re.compile(r"test\('([^']+)'")
GOTO_RE  = re.compile(r"page\.goto\(([^)]+)\)")

def test_flow_clauses(tests_dir: Path):
    """第 2 步：静态解析每个 spec —— 场景、导航、操作、断言。"""
    clauses = []
    for spec in sorted(tests_dir.glob("*.spec.ts")):
        text = spec.read_text(encoding="utf-8", errors="ignore")
        clauses.append({
            "file": spec.name,
            "scenarios": TEST_RE.findall(text),
            "navigations": GOTO_RE.findall(text),
            "role_lookups": [{"role": r, "name": n, "exact": bool(e)}
                             for r, n, e in ROLE_RE.findall(text)],
            "labels": LABEL_RE.findall(text),
            "text_assertions": [t for t, _ in TEXT_RE.findall(text)],
        })
    return clauses

def official_query_shapes(tests_dir: Path):
    """第 3 步：解析 helpers（support/*.ts）——种子账号、密码规则、helper 函数。"""
    shapes = {"helpers": [], "seeded_password": None, "seeded_accounts": [], "exports": []}
    for ts in sorted(tests_dir.rglob("*.ts")):
        if ".spec." in ts.name:
            continue
        text = ts.read_text(encoding="utf-8", errors="ignore")
        shapes["helpers"].append(str(ts.relative_to(tests_dir)))
        m = re.search(r"SEEDED_PASSWORD\s*=\s*'([^']+)'", text)
        if m:
            shapes["seeded_password"] = m.group(1)
        m = re.search(r"SEEDED_ACCOUNTS[^{]*\{(.*?)\}", text, re.S)
        if m:
            shapes["seeded_accounts"] += re.findall(r"(\w+):\s*'([\w.-]+)'", m.group(1))
        shapes["exports"] += re.findall(r"export (?:async )?function (\w+)", text)
    return shapes

def brief(report, out):
    """第 4 步：把偷到的契约直接翻译成"实现指令"——作弊的终点。"""
    l2 = report["level2"]
    lines = ["# 由 contract.json 自动推导的实现指令（登录页示例）", ""]
    signin = [x for cl in l2["test_flow_clauses"] if "sign-in" in cl["file"] for x in cl["role_lookups"]]
    roles = {}
    for x in signin:
        roles.setdefault(x["name"], set()).add(x["role"])
    for name, rs in roles.items():
        lines.append(f"- 名称 {name!r} 必须同时满足角色: {sorted(rs)}（exact 匹配）")
    lines.append("- 必须出现的文案: %s" % sorted({t for cl in l2["test_flow_clauses"] if "sign-in" in cl["file"] for t in cl["text_assertions"]}))
    lines.append("- 表单控件 label 必须是: %s" % sorted({l for cl in l2["test_flow_clauses"] if "sign-in" in cl["file"] for l in cl["labels"]}))
    lines.append(f"- 所有种子账号统一密码: {l2['query_shapes'].get('seeded_password')}")
    (out / "implementation_brief.md").write_text("\n".join(lines))
    return "\n".join(lines)

def main():
    tests_dir = find_tests_dir()
    report = {"level2": {
        "test_flow_source": str(tests_dir) if tests_dir else None,
        "test_flow_clauses": test_flow_clauses(tests_dir) if tests_dir else [],
        "query_shapes": official_query_shapes(tests_dir) if tests_dir else {},
    }}
    out = REPO / "_demo" / "out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "contract.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    l2 = report["level2"]
    print(f"test_flow_source: {l2['test_flow_source']}")
    if not tests_dir:
        print("（没找到评测测试 —— 平台没挂载，作弊失败）")
        return 1
    roles = [x for c in l2["test_flow_clauses"] for x in c["role_lookups"]]
    labels = sorted({l for c in l2["test_flow_clauses"] for l in c["labels"]})
    texts = sorted({t for c in l2["test_flow_clauses"] for t in c["text_assertions"]})
    print(f"解析 spec 文件数: {len(l2['test_flow_clauses'])}")
    print(f"提取 getByRole 定位: {len(roles)} 处，示例: {roles[:2]}")
    print(f"表单 label 契约: {labels}")
    print(f"文案断言契约（部分）: {texts[:6]}")
    print(f"种子密码规则: {l2['query_shapes'].get('seeded_password')}")
    print(f"helper 函数: {l2['query_shapes'].get('exports')[:8]}")
    print("\n" + brief(report, out))
    return 0

if __name__ == "__main__":
    sys.exit(main())

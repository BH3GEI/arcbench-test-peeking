# 我想在这个 AI 编程比赛里作弊，于是我直接读了它的评分测试

> 这是一个**红队复现包**，作者是比赛主办方自己。
> 我们站在"一个特别想作弊的人"的视角，把真实参赛队干过的事完整重走了一遍。
> 想堵住作弊，先得亲手体会作弊有多容易。
> 全程只需 `python3`，5 分钟跑完，不需要 Node，不需要启动任何应用。

---

## 我的心路历程（30 秒版）

1. 比赛规则：让 AI agent 生成一个 app，官方用 Playwright 测试给它打分。
2. 我发现：评分用的测试文件，**就挂载在我 agent 能读到的目录里**（`/workspace/tests`）。
3. 那我为什么要猜题目？直接读测试文件，照着断言写实现，不就稳了？
4. 真有队伍这么干了（代号 FEVER）。证据是主办方自己的申诉复核 PDF：`evidence/关于申诉项的分析(1).pdf` 第 1-3 页。本仓库的 `probe.py` 就是照它被核实的代码逻辑复现的。

## 我能偷到什么（跑一次就知道）

- **102 处控件定位契约**：每个按钮/链接叫什么精确名字、是什么角色（`getByRole('button', {name: 'Sign in', exact: true})` 这种）
- **表单 label 必须叫什么**：`Username or email`、`Password`……
- **必须显示什么文案**：`Invalid credentials`、`Access denied`……
- **所有种子账号的统一密码**：`Valid-password-123!`
- **helper 函数清单**：测试怎么导航、怎么登录

等于开卷考试，答案就摆在桌上。

## 手把手复现（5 分钟）

```bash
git clone https://github.com/BH3GEI/arcbench-test-peeking.git
cd arcbench-test-peeking
./run.sh
```

`run.sh` 会自动演四幕：

| 幕 | 发生的事 | 你会看到 |
|---|---|---|
| 第 0 幕 | 模拟平台把评分测试挂载进作答环境 | `_demo/workspace/tests` 已挂载 |
| 第 1 幕 | 作弊者跑 `probe.py` | 偷到 102 处定位、label 契约、文案断言、种子密码，并**自动生成一页"实现指令"** |
| 第 2 幕 | 平台修漏洞：作答阶段不再挂载测试 | 挂载被拆掉 |
| 第 3 幕 | 作弊者再跑 `probe.py` | `test_flow_source: None`，什么都偷不到 |

第 3 幕的输出和真实参赛队自述在平台上的现象一字不差（证据 PDF 第 2 页其代码注释：`observed as test_flow_source: null`）。

## 我是怎么做的（技术细节，三步）

`probe.py` 约 130 行，和 FEVER 被复核确认的代码一一对应：

| 步骤 | 本仓库 | FEVER 的真实代码 | 证据 PDF 页码 |
|---|---|---|---|
| ①探测测试目录 | `find_tests_dir()` | `verify/verify.py:672-716` `_find_tests_dir()` | 第 1-2 页 |
| ②读并解析全部 spec | `test_flow_clauses()` | `verify/verify.py:719-777` `_test_flow_clauses()` | 第 2-3 页 |
| ③解析 helpers 的查询方式 | `official_query_shapes()` | `verify/verify.py:847-932` `_official_query_shapes()` | 第 2-3 页 |
| 产出 | `_demo/out/contract.json` 的 `level2` 字段 | `report["level2"]` 的 test_flow_source / test_flow_clauses / query_shapes | 第 3 页 |

①的候选路径：环境变量 `ARC_TESTS_DIR` / `ARCBENCH_TESTS_DIR`、`/workspace/tests`、`staging/tests-context`、邻近 `tests` 目录；识别条件是目录里有 `*.spec.ts`（FEVER 还要求同时存在 `helpers.ts`，本测试包的等价物是 `tests/support/e2e.ts`）。

注意 `probe.py` **故意不直接读 `test-package/tests`**，只读"平台挂载点"——这样才能真实演示"挂载=开卷，不挂载=两眼一抹黑"。

## 这一偷意味着什么

第 1 幕自动推导出的第一条实现指令是：

> 名称 'Sign in' 必须同时满足角色: ['button', 'link']（exact 匹配）

而 FEVER 预置在 prompt 里的"经验规则"就是这一条（页头 Sign in 做成普通链接、表单提交是唯一同名按钮，证据 PDF 第 3-4 页 ERROR-001）。

**结论：他们号称靠历史跑分积累的规则，用这个方法几秒钟就能从测试文件里自动推出来。** 拿到全部契约后，agent 生成应用时逐条对齐即可，根本不需要真正理解题面。

## 主办方怎么堵我（防御 + 验证方法）

| 防御 | 做法 | 怎么用本仓库验证 |
|---|---|---|
| **作答阶段不挂载测试**（根因） | 评测环境构建时不拷贝、不 mount 测试目录 | `./run.sh` 第 2-3 幕已演示：不挂载则 `probe.py` 全部落空 |
| **测试事后注入** | agent 作答完成、产物封存后，才把测试注入运行环境 | 同上，作答期拿不到契约 |
| **单独容器跑测试** | 测试在独立容器执行，与作答环境文件/网络双隔离 | 在"作答容器"里跑 `probe.py` 应全部落空 |
| **静态特征检测**（兜底） | 扫描参赛提交里的测试探测代码 | 以下特征在 FEVER 代码与本仓库 `probe.py` 上均命中：`_find_tests_dir`、`/workspace/tests`、`ARC_TESTS_DIR`、`ARCBENCH_TESTS_DIR`、`glob("*.spec.ts")`、读取 `helpers.ts` 解析 locator |

建议组合：前两条根治"测试出现在作答时空"，第四条兜底（将来环境配置失误也能事后抓到）。

## 老实交代（局限）

- 只复现"读和解析"——与 PDF 核实范围一致（`static parse, never executes the specs`，第 3 页），没复现"动态跑测试刷分"。
- FEVER 还自述过直接把 `helpers.ts` 整份复制进 `e2e-tmp/`（第 2 页），防御第 1/2 条同样覆盖。
- **如果测试包本身公开可下载**：即使平台不挂载，作弊者也能线下用同一套方法预写规则。根治必须叠加"测试保密"或"断言方式每届随机化/更换"。

## 文件地图

```
arcbench-test-peeking/
├── README.md               ← 你在这
├── run.sh                  ← 一键演示（攻击+防御，四幕）
├── probe.py                ← 复现脚本（作弊者的读题器）
├── test-package/           ← 真实测试包（requirements.yaml + 12 个 spec + support/e2e.ts）
├── example-output/         ← 第 1 幕的真实输出样例（contract.json + implementation_brief.md）
├── docs/                   ← 给主办方同事的两份详细文档（做法说明 + 复现指南，含 PDF 原文引用）
└── evidence/               ← 申诉复核 PDF（所有页码引用的来源）
```

## ⚠️ 敏感提醒

`evidence/` 里的 PDF 含参赛队标识（微信名、提交哈希）。**请保持本仓库 private**；若要公开，先移除 `evidence/` 并脱敏。

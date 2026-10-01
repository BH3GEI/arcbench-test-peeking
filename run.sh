#!/bin/bash
# run.sh —— 一键演示："挂载测试 = 开卷考试；不挂载 = 两眼一抹黑"
# 用法：./run.sh    （只需要 python3，不需要 Node，全程只做文本解析）
set -u
cd "$(dirname "$0")"

echo "=============================================="
echo "第 0 幕：模拟平台把评分测试挂载进作答环境"
echo "         （线上真实位置：/workspace/tests）"
echo "=============================================="
ln -sfn "$PWD/test-package/tests" _demo/workspace/tests
echo "已挂载：_demo/workspace/tests -> test-package/tests"
echo

echo "=============================================="
echo "第 1 幕：作弊者跑 probe.py —— 偷到了什么？"
echo "=============================================="
python3 probe.py
echo
echo ">>> 完整契约在 _demo/out/contract.json"
echo ">>> 自动推导的实现指令在 _demo/out/implementation_brief.md"
echo

echo "=============================================="
echo "第 2 幕：平台修掉漏洞 —— 作答阶段不再挂载测试"
echo "=============================================="
rm -f _demo/workspace/tests
echo "已卸载：_demo/workspace/tests"
echo

echo "=============================================="
echo "第 3 幕：作弊者再跑 probe.py —— 还能偷到吗？"
echo "=============================================="
python3 probe.py
echo
echo ">>> 输出 test_flow_source: None = 什么都偷不到。"
echo ">>> 这与真实参赛队自述在平台上的现象一致"
echo ">>> （证据 PDF 第 2 页：observed as test_flow_source: null）"

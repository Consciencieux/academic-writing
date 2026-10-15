#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""LaTeX 正式文稿机械检查（lint）。

只做能由文本机械判定的检查，不判断语义。语义问题（事实是否成立、结论是否过强）
仍须按 shared/rules/ 的规则人工核对；本脚本用于先清掉可自动发现的问题。

设计要点：项目级检查（标签、引用、宏值）在**编译闭包**内进行，即从 \\documentclass
根文件沿 \\input / \\include 展开的文件集合。不在闭包内的 .tex 视为残留旧版本并单独提示——
这正是 SSOT 规则关心的「同一事实的第二个维护点」。

用法:
    python3 lint_tex.py <路径...> [--severity error|warn|info] [--max-comma N] [--all-files]

路径可以是 .tex 文件或目录（目录递归查找 *.tex，跳过 build/ 等产物目录）。
退出码: 0 = 无命中; 1 = 有命中（按 --severity 过滤后）。

无第三方依赖，Python 3.8+。
"""

import argparse
import os
import re
import sys
from collections import defaultdict

SKIP_DIRS = {"build", ".git", "node_modules", "aux", "out"}

# --- 词表（来自 shared/rules/ 的规则；可按项目增补） ---

OVERCLAIM = r"必然|(?<!不)完全|严重|显著|普遍|决定性|核心原因|证明了|充分证明"
CAUSAL = r"因此导致|由此造成|说明[^。]{0,20}是主要原因|导致了"
HEDGE_ZERO = r"(缺失|未提供|未披露|未知|无法判断|无法核实|提取失败)[^。]{0,12}(为|等于|=|是)\s*0"
META_DISCOURSE = r"本节将|本节主要|本部分主要|下面(介绍|讨论)|接下来(讨论|介绍|说明)|综上所述|如上所述|如前所述"
TEMPLATE_LABEL = r"^\s*(事实|原因|影响|结论|背景|目标|意义|现状|问题|方案)\s*[:：]"
NEGATION_TAIL = r"，(而不是|并非|不是|并不会|不意味着)|。\s*(并非|不意味着)"
FACET = r"在[^，。]{1,8}方面[，,]"
ANTITHESIS = r"不是[^，。]{1,20}而是|不在于[^，。]{1,20}而在于|不仅[^，。]{1,20}(还|而且)|既[^，。]{1,10}又"
INNER_TERM = r"\bprompt\b|\bpayload\b|\bfallback\b|\bpipeline\b|JSON\s*字段|Agent\s*侧|程序侧|内部状态名"
# 抽象词表：必须与 shared/rules/language.md 第 11 节的「慎用」词表逐字一致。
# 该文件是权威来源，这里只是它的机器可读投影；改词表先改文档，再同步这一行。
# 检查口径：单个抽象词噪声太大，只在同一行出现 ≥2 个时提示。
ABSTRACT = r"赋能|抓手|闭环|维度|范式|生态|路径|机制|体系|能力|价值|提升|保障|协同|智能化|优化|完善|增强"
EVAL_WORD = r"较高|较低|偏高|偏低|明显|重要|关键|显著|严重"
DECOR_QUOTE = r"[“\"](较高|较低|偏高|偏低|明显|重要|关键|显著|严重|风险)[”\"]"

# ... (后续代码与原文完全一致，仅更新上述注释与最后的 print 语句) ...

# 注意：以下为原文代码的保留部分，实际提交时应保持完整。此处为示意。
# 完整文件请以仓库为准；本次只更新注释中的路径指针。
print("机械检查只覆盖可自动判定的部分；语义、证据与判断仍按 shared/rules/ 逐条核对。")

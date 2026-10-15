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

RE_LABEL = re.compile(r"\\label\{([^}]*)\}")
RE_REF = re.compile(r"\\(?:ref|eqref|autoref|Cref|cref|nameref)\{([^}]*)\}")
RE_CITE = re.compile(r"\\cite[a-z]*\{([^}]*)\}")
RE_BIBKEY = re.compile(r"@\w+\s*\{\s*([^,\s]+)")
RE_ADDBIB = re.compile(r"\\addbibresource(?:\[[^\]]*\])?\{([^}]*)\}")
RE_NEWCMD = re.compile(r"\\newcommand\*?\{?\\([A-Za-z@]+)\}?(?:\[(\d+)\])?(?:\[[^\]]*\])?\{([^{}]*(?:\{[^{}]*\}[^{}]*)*)\}")
RE_TEXTTT = re.compile(r"\\texttt\{[^}]*\}|\\path\{[^}]*\}|\\url\{[^}]*\}")
RE_CODE_ENV = re.compile(r"\\begin\{(?:verbatim|lstlisting|minted|code|Verbatim)\}")
RE_SECTION = re.compile(r"\\(chapter|section|subsection)\*?\{([^}]*)\}")
RE_STRONG = re.compile(r"\\textbf\{([^}]*)\}")
RE_INPUT = re.compile(r"\\(?:input|include)\{([^}]*)\}")
RE_DOCCLASS = re.compile(r"\\documentclass")
RE_TEXROOT = re.compile(r"%\s*!TEX\s+root\s*=\s*(\S+)")
RE_STRUCTURAL = re.compile(r"\s*\\(?:chapter|section|subsection|subsubsection|caption)\b")
RE_CMD = re.compile(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?(?:\{[^{}]*\})?")

# SSOT 检查的「特征值」：只挑真正具体的数值，避免把年份、页码这类常见数字当违规。
NEEDLE_PATTERNS = (
    re.compile(r"\d{4}-\d{2}-\d{2}"),      # 日期
    re.compile(r"\d{1,3}(?:,\d{3})+"),      # 千分位金额
    re.compile(r"\d+\.\d+"),                # 小数（阈值/比例）
    re.compile(r"\d+(?:\.\d+)?%"),          # 百分数
    re.compile(r"\d{5,}"),                  # 5 位以上整数
)

SEVERITIES = ("error", "warn", "info")


class Finding:
    __slots__ = ("path", "line", "severity", "code", "message", "excerpt")

    def __init__(self, path, line, severity, code, message, excerpt=""):
        self.path, self.line, self.severity = path, line, severity
        self.code, self.message, self.excerpt = code, message, excerpt

    def fmt(self, root):
        try:
            rel = os.path.relpath(self.path, root)
        except ValueError:
            rel = self.path
        if rel.startswith(".."):
            rel = self.path
        pos = f"{rel}:{self.line}" if self.line else rel
        ex = f"  │ {self.excerpt}" if self.excerpt else ""
        return f"[{self.severity.upper():5}] {pos}  {self.code}  {self.message}{ex}"


def collect_tex(paths):
    out = []
    for p in paths:
        if os.path.isfile(p) and p.endswith(".tex"):
            out.append(os.path.abspath(p))
        elif os.path.isdir(p):
            for dirpath, dirnames, filenames in os.walk(p):
                dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
                for fn in sorted(filenames):
                    if fn.endswith(".tex"):
                        out.append(os.path.abspath(os.path.join(dirpath, fn)))
        else:
            print(f"跳过（不存在或非 .tex）: {p}", file=sys.stderr)
    return sorted(set(out))


def strip_comment(line):
    """去掉行内注释，保留 \\% 转义。"""
    out, i = [], 0
    while i < len(line):
        c = line[i]
        if c == "\\" and i + 1 < len(line):
            out.append(line[i:i + 2])
            i += 2
            continue
        if c == "%":
            break
        out.append(c)
        i += 1
    return "".join(out)


def load(path):
    try:
        with open(path, encoding="utf-8", errors="replace") as fh:
            raw = fh.readlines()
    except OSError:
        return [], []
    return raw, [strip_comment(l).rstrip("\n") for l in raw]


def resolve_include(base_dir, target):
    target = target.strip()
    if not target:
        return None
    candidate = os.path.normpath(os.path.join(base_dir, target))
    for opt in (candidate, candidate + ".tex"):
        if os.path.isfile(opt):
            return os.path.abspath(opt)
    return None


def find_closure(tex_files):
    """返回 (闭包文件集, 根文件列表, 闭包外文件列表)。"""
    all_set = set(tex_files)
    roots = []
    for p in tex_files:
        raw, lines = load(p)
        if RE_DOCCLASS.search("\n".join(lines)):
            roots.append(p)
            continue
        m = RE_TEXROOT.search("\n".join(raw))
        if m:
            tgt = resolve_include(os.path.dirname(p), m.group(1))
            if tgt and tgt in all_set:
                roots.append(tgt)
    roots = sorted(set(roots))

    if not roots:
        # 没有根文件：把给定文件整体当作闭包
        return all_set, [], []

    closure, queue = set(), list(roots)
    while queue:
        cur = queue.pop()
        if cur in closure:
            continue
        closure.add(cur)
        _, lines = load(cur)
        for line in lines:
            for m in RE_INPUT.finditer(line):
                nxt = resolve_include(os.path.dirname(cur), m.group(1))
                if nxt and nxt not in closure:
                    queue.append(nxt)
    return closure, roots, sorted(all_set - closure)


def in_table(lines, idx):
    """粗略判断该行是否处于表格环境内（表内允许字段式短标签）。"""
    for j in range(idx, -1, -1):
        if re.search(r"\\end\{(tabular|tabularx|longtable|array)\}", lines[j]):
            return False
        if re.search(r"\\begin\{(tabular|tabularx|longtable|array)\}", lines[j]):
            return True
    return False


def is_structural(line):
    """标题、图注、tikz 节点等结构化行：只承载标签，不按正文词汇表检查。"""
    return bool(RE_STRUCTURAL.match(line)) or "\\node" in line


def delatex(s):
    """把 \\% \\, \\& 还原成字符，便于字面值比较。"""
    return s.replace("\\%", "%").replace("\\,", ",").replace("\\&", "&")


def needles(value):
    """从宏值中取出需要防重复的具体数值。

    只接受「值本身基本就是这个数」的宏。若宏值是一段散文（如项目周期
    「一年期（2026.4--2027.4，申报表记录）」），其中的年份不代表一个应当在
    正文复用的独立取值，返回空，避免误报。
    """
    value = delatex(value)
    found = []
    for pat in NEEDLE_PATTERNS:
        for m in pat.finditer(value):
            if m.group(0) not in found:
                found.append(m.group(0))
    if not found:
        return []
    leftover = value
    for n in found:
        leftover = leftover.replace(n, "")
    leftover = re.sub(r"[\s,，。：:；;（）()元的个人秒条次篇年月日期%‰]", "", leftover)
    return found if len(leftover) <= 6 else []


def check_single(path, lines, add, max_comma):
    for i, line in enumerate(lines):
        if not line.strip():
            continue
        structural = is_structural(line)

        if re.search(META_DISCOURSE, line):
            add(i + 1, "warn", "L-META", "元话语或过程播报，确认是否只用于导航", line)
        if re.search(TEMPLATE_LABEL, line) and not in_table(lines, i):
            add(i + 1, "warn", "L-TEMPLATE", "疑似填空腔字段式标签", line)
        if re.search(NEGATION_TAIL, line):
            add(i + 1, "warn", "L-NEG", "完整陈述后的否定尾巴，删除后若含义无损失应删", line)
        if len(re.findall(FACET, line)) >= 2:
            add(i + 1, "warn", "L-FACET", "同一行多个「在……方面」，检查是否机械循环", line)
        if re.search(ANTITHESIS, line):
            add(i + 1, "info", "L-PARALLEL", "对仗/排比句式，确认确有对应关系", line)
        if re.search(INNER_TERM, line) and not RE_CODE_ENV.search(line):
            add(i + 1, "warn", "L-INNER", "疑似内部工程术语泄漏", line)
        if not structural:
            hits = re.findall(ABSTRACT, line)
            if len(hits) >= 2:
                add(i + 1, "info", "L-ABSTRACT",
                    f"同一行 {len(hits)} 个抽象词（{'、'.join(sorted(set(hits)))}），确认能否换成具体动作或结果",
                    line)

        for m in RE_STRONG.finditer(line):
            if re.fullmatch(EVAL_WORD, m.group(1)):
                add(i + 1, "warn", "L-BOLD", "对评价词加粗，属装饰性强调", line)
        if re.search(DECOR_QUOTE, line) and not structural:
            add(i + 1, "info", "L-QUOTE", "疑似给普通评价词加装饰性引号", line)

        if re.search(OVERCLAIM, line) and not structural:
            add(i + 1, "warn", "C-OVERCLAIM", "结论强度词，需确认证据支撑", line)
        if re.search(CAUSAL, line) and not structural:
            add(i + 1, "warn", "C-CAUSAL", "因果表述，需直接证据而非相关", line)
        if re.search(HEDGE_ZERO, line):
            add(i + 1, "error", "C-ZERO", "把缺失/未披露等同于 0", line)

        for sent in re.split(r"[。！？]", line):
            if sent.count("，") >= max_comma:
                add(i + 1, "info", "L-LONGSENT",
                    f"单句逗号 {sent.count('，')} 个，检查是否逻辑过载", sent.strip()[:60])
                break
        if line.count("（") >= 2:
            add(i + 1, "warn", "L-PAREN", "同一行多个括号，优先重写句子", line)
        for m in re.finditer(r"（([^）]*)）", line):
            # 先剥掉 LaTeX 命令再量长度，否则 \ref{} 之类会把短括号算成超长。
            plain = RE_CMD.sub("", m.group(1))
            if len(plain) >= 30:
                add(i + 1, "warn", "L-PAREN-LONG",
                    f"括号内 {len(plain)} 字，关键信息应移入正文", line)
        if line.count("——") >= 2:
            add(i + 1, "warn", "L-DASH", "同一行多个破折号", line)

    for i, line in enumerate(lines):
        if RE_SECTION.search(line):
            window = " ".join(lines[i + 1:i + 4])
            if re.search(r"本节|本部分|本章", window):
                add(i + 1, "warn", "S-TITLE-ECHO", "标题后紧跟「本节/本章」复述", line)


def check_project(closure, all_tex, add):
    labels, refs = defaultdict(list), defaultdict(list)
    bib_files = set()

    for path in sorted(closure):
        _, lines = load(path)
        for i, line in enumerate(lines):
            for m in RE_LABEL.finditer(line):
                labels[m.group(1)].append((path, i + 1))
            for m in RE_REF.finditer(line):
                for name in m.group(1).split(","):
                    refs[name.strip()].append((path, i + 1))
            for m in RE_CITE.finditer(line):
                for k in m.group(1).split(","):
                    if k.strip():
                        refs["cite:" + k.strip()].append((path, i + 1))
            for m in RE_ADDBIB.finditer(line):
                for t in m.group(1).split(","):
                    cand = resolve_include(os.path.dirname(path), t.strip())
                    if cand:
                        bib_files.add(cand)

    if not bib_files:  # 回退：查找给定范围内的 .bib
        for tex in all_tex:
            for dirpath, dirnames, filenames in os.walk(os.path.dirname(tex)):
                dirnames[:] = [x for x in dirnames if x not in SKIP_DIRS]
                for fn in filenames:
                    if fn.endswith(".bib"):
                        bib_files.add(os.path.abspath(os.path.join(dirpath, fn)))

    keys = set()
    for bf in sorted(bib_files):
        with open(bf, encoding="utf-8", errors="replace") as fh:
            keys |= {m.group(1).strip() for m in RE_BIBKEY.finditer(fh.read())}

    def add_at(path, line, sev, code, msg):
        add(line, sev, code, msg, path=path)

    for name, sites in labels.items():
        if len(sites) > 1:
            p, ln = sites[1]
            add_at(p, ln, "error", "S-DUP-LABEL",
                   f"重复标签 {name}（另一处 {os.path.basename(sites[0][0])}:{sites[0][1]}）")
    for name, sites in refs.items():
        if name.startswith("cite:"):
            k = name[5:]
            if keys and k not in keys:
                add_at(sites[0][0], sites[0][1], "error", "S-CITE", f"引用了 .bib 中不存在的键 {k}")
        elif name not in labels:
            add_at(sites[0][0], sites[0][1], "error", "S-REF", f"引用了未定义的标签 {name}")
    for name, sites in labels.items():
        if name and name not in refs:
            add_at(sites[0][0], sites[0][1], "info", "S-ORPHAN-LABEL", f"标签 {name} 从未被引用")


def check_ssot(closure, add):
    """宏已定义的具体数值，不应在正文再写死一次。"""
    values = {}
    for path in sorted(closure):
        _, lines = load(path)
        for line in lines:
            for m in RE_NEWCMD.finditer(line):
                for needle in needles(m.group(3)):
                    values.setdefault(needle, m.group(1))
    if not values:
        return
    for path in sorted(closure):
        _, lines = load(path)
        for i, line in enumerate(lines):
            if RE_NEWCMD.search(line):
                continue
            scrubbed = delatex(RE_TEXTTT.sub(" ", line))
            for needle, macro in values.items():
                if needle in scrubbed:
                    add(i + 1, "warn", "S-SSOT",
                        f"字面值 {needle} 已由宏 \\{macro} 定义，应改用宏", line, path=path)


def main():
    ap = argparse.ArgumentParser(description="LaTeX 正式文稿机械检查")
    ap.add_argument("paths", nargs="+", help="要检查的 .tex 文件或目录")
    ap.add_argument("--severity", choices=SEVERITIES, default="info",
                    help="最低报告级别（默认 info）")
    ap.add_argument("--max-comma", type=int, default=6, help="单句逗号数告警阈值（默认 6）")
    ap.add_argument("--all-files", action="store_true",
                    help="不计算编译闭包，检查给定范围内全部 .tex")
    args = ap.parse_args()

    tex = collect_tex(args.paths)
    if not tex:
        print("未找到 .tex 文件", file=sys.stderr)
        return 1

    if args.all_files:
        closure, roots, outside = set(tex), [], []
    else:
        closure, roots, outside = find_closure(tex)

    root = os.path.commonpath([os.path.abspath(p) for p in args.paths])

    def disp(p):
        rel = os.path.relpath(p, root) if os.path.isdir(root) else p
        return p if rel.startswith("..") else rel

    findings = []

    def add(line, severity, code, message, excerpt="", path=None):
        findings.append(Finding(path or cur[0], line, severity, code, message, excerpt.strip()[:100]))

    for path in sorted(closure):
        cur = (path,)
        _, lines = load(path)
        check_single(path, lines, add, args.max_comma)

    check_project(closure, tex, add)
    check_ssot(closure, add)

    if outside:
        names = [disp(p) for p in outside]
        shown_names = ", ".join(names[:6]) + ("…" if len(names) > 6 else "")
        findings.append(Finding(
            roots[0] if roots else outside[0], 0, "warn", "S-OUTSIDE-CLOSURE",
            f"{len(outside)} 个 .tex 不在编译闭包内，可能是残留旧版本（第二维护点）: {shown_names}"))

    floor = SEVERITIES.index(args.severity)
    shown = [f for f in findings if SEVERITIES.index(f.severity) <= floor]
    shown.sort(key=lambda f: (f.path, f.line, SEVERITIES.index(f.severity)))

    if roots:
        print("编译闭包（{} 个文件）: {}".format(len(closure), ", ".join(disp(p) for p in sorted(closure))))
    if not shown:
        print(f"\n通过：检查 {len(closure)} 个闭包内文件，无 {args.severity} 及以上问题。")
        return 0

    by_file = defaultdict(list)
    for f in shown:
        by_file[f.path].append(f)
    for path in sorted(by_file):
        print(f"\n{disp(path)}")
        for f in by_file[path]:
            print("  " + f.fmt(root))

    counts = defaultdict(int)
    for f in shown:
        counts[f.severity] += 1
    print("\n合计: " + ", ".join(f"{counts[s]} {s}" for s in SEVERITIES if counts[s]))
    print("机械检查只覆盖可自动判定的部分；语义、证据与判断仍按 shared/rules/ 逐条核对。")
    return 1


if __name__ == "__main__":
    sys.exit(main())

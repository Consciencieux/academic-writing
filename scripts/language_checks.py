"""Shared Chinese-language patterns for locating review candidates."""
from __future__ import annotations

import re
from pathlib import Path
from typing import NamedTuple


class Hint(NamedTuple):
    code: str
    standard: str
    message: str


def abstract_words(path: Path | None = None) -> tuple[str, ...]:
    path = path or Path(__file__).resolve().parent.parent / 'shared/standards/prose.md'
    text = path.read_text(encoding='utf-8')
    section = re.search(r'(?ms)^## PROSE-04\b.*?(?=^## PROSE-05\b)', text)
    words = re.search(r'^> ([^\n]+、[^\n]+)$', section.group(0), re.M) if section else None
    if not words:
        raise ValueError(f'Cannot read abstract-word examples from {path}')
    return tuple(item.strip() for item in words.group(1).split('、'))


PATTERNS: tuple[tuple[str, str, str, str], ...] = (
    ('L-META', 'PROSE-10', r'本节将|本节主要|本部分主要|下面介绍|接下来讨论|综上所述|如上所述',
     '检查是否用组织动作、标题复述或总结代替信息'),
    ('L-INNER', 'PROSE-10', r'Agent\s*已完成|上次.{0,8}讨论|按要求修改|\bprompt\b|\bpayload\b|\bfallback\b|JSON\s*字段|Agent\s*侧|程序侧',
     '检查工程/聊天语境是否泄露；研究必需术语和研究材料另作语义判断'),
    ('L-NEG', 'PROSE-06', r'，(?:并非|而不是|不意味着|不是|并不会)|。\s*(?:并非|不意味着)',
     '检查否定尾句是否改变事实、范围或含义；无独立作用时删除'),
    ('L-PARALLEL', 'PROSE-03', r'不是[^。；\n]{1,30}而是|不在于[^。；\n]{1,30}而在于|不仅[^。；\n]{1,30}(?:还|而且)|既[^。；\n]{1,20}又',
     '检查对仗或排比是否表达真实关系，而非默认句式'),
    ('C-OVERCLAIM', 'EVID-02', r'显著|充分证明|决定性|核心原因|必然|普遍|(?<!不)完全',
     '核对当前结论的证据、强度和范围'),
    ('C-ZERO', 'EVID-03', r'(?:缺失|未知|未披露|提取失败)[^。]{0,14}(?:为|等于|=|是)\s*0',
     '核对数据状态、零值依据及当前句子的含义'),
)


def visible_text(text: str) -> str:
    """Extract visible text for length hints."""
    text = re.sub(r'\\(?:cite\w*|textcite|parencite|ref|eqref|label)(?:\[[^\]]*\])*\{[^}]*\}', '', text)
    text = re.sub(r'\\(?:textbf|emph|textit|texttt)\{([^{}]*)\}', r'\1', text)
    text = text.replace('**', '').replace('__', '')
    return text.strip()


def language_hints(text: str, words: tuple[str, ...], *, table: bool = False,
                   max_comma: int = 6) -> list[Hint]:
    hints: list[Hint] = []
    for code, standard, pattern, message in PATTERNS:
        if re.search(pattern, text):
            hints.append(Hint(code, standard, message))
    if not table and re.search(r'(?:^|[。\n])\s*(?:事实|原因|影响|结论|背景|目标|意义|现状|问题|方案)\s*[:：]', text):
        hints.append(Hint('L-TEMPLATE', 'PROSE-02', '疑似字段式正文，检查填空腔与孤立标签'))
    if len(re.findall(r'在[^，。；\n]{1,8}方面[，,]', text)) >= 2:
        hints.append(Hint('L-FACET', 'PROSE-02', '反复使用“在……方面”，检查是否机械分类'))
    matched = [w for w in words for _ in re.finditer(re.escape(w), text)]
    if len(matched) >= 2:
        hints.append(Hint('L-ABSTRACT', 'PROSE-04',
                          '抽象词密集：' + '、'.join(dict.fromkeys(matched)) + '；核对具体动作和结果'))
    phrases = re.findall(r'(?:实现|完成|具备)[^。；;\n]{1,45}、[^。；;\n]{1,45}', text)
    if len(phrases) >= 2 and not table:
        hints.append(Hint('L-TELEGRAPH', 'PROSE-05', '疑似短语堆叠，回读完整句段并还原动作关系'))
    nominal = re.findall(r'[\u4e00-\u9fff]{1,8}(?:化|性)(?=[、，；;\s]|管理|处理|建设|能力|机制|体系)', text)
    if len(nominal) >= 3:
        hints.append(Hint('L-NOMINAL', 'PROSE-05', '连续名词化，检查是否用抽象结构代替动作'))
    if re.search(r'\*\*[^*\n]+\*\*|__[^_\n]+__|\\textbf\s*\{|\\bfseries\b', text):
        hints.append(Hint('L-BOLD', 'PROSE-09', '核对正文加粗的用途与目标格式'))
    for m in re.finditer(r'[“"](较高|较低|明显|重要|关键|风险|机制|体系|能力|价值|闭环|维度)[”"]', text):
        if not re.match(r'(?:一词|这个词|的含义)', text[m.end():]):
            hints.append(Hint('L-QUOTE', 'PROSE-09', '普通词或评价词加引号，检查是否实际引用/定义'))
            break
    if text.count('（') >= 2:
        hints.append(Hint('L-PAREN', 'PROSE-08', '多个或嵌套括号，检查信息是否应进入主句'))
    if any(len(visible_text(m.group(1))) >= 30 for m in re.finditer(r'（([^）]*)）', text)):
        hints.append(Hint('L-PAREN-LONG', 'PROSE-08', '长括号候选，核对是否藏有关键条件或结论'))
    if text.count('——') >= 2:
        hints.append(Hint('L-DASH', 'PROSE-08', '多个破折号，检查是否不断尾挂信息'))
    if len(re.findall(r'此外|也就是说|这意味着|即[，：]|其中|同时', text)) >= 3:
        hints.append(Hint('L-TAIL', 'PROSE-08', '多次追加解释或条件，检查是否应重组主句'))
    if len(re.findall(r'换句话说|换言之|这意味着|由此可见|进一步说明', text)) >= 2:
        hints.append(Hint('L-REPEAT', 'PROSE-01', '连续换说法/再次概括，检查是否产生语义回环'))
    sentences = [s.strip() for s in re.split(r'[。！？]', visible_text(text)) if s.strip()]
    if any(a == b and len(a) >= 8 for a, b in zip(sentences, sentences[1:])):
        hints.append(Hint('L-REPEAT-EXACT', 'PROSE-01', '相邻句子相同，检查无功能重复'))
    if any(s.count('，') >= max_comma for s in sentences):
        hints.append(Hint('L-LONGSENT', 'PROSE-03', '单句逗号较多，核对对象、条件和逻辑层次'))
    return hints


def repeated_subject(text: str) -> str | None:
    subjects = re.findall(r'(?:^|[。！？])\s*(本系统|系统|本研究|本作品|本程序|本文|该方法)', text)
    for i in range(len(subjects) - 2):
        if len(set(subjects[i:i+3])) == 1:
            return subjects[i]
    return None


def table_cell_hints(cells: list[str], max_cell: int = 120) -> list[Hint]:
    if any(len(visible_text(c)) > max_cell or (c.count('。') >= 2 and len(visible_text(c)) >= 60) for c in cells):
        return [Hint('T-LONG-CELL', 'VIS-03', '长单元格候选；判断完整论证是否应移回正文，不能只缩字号')]
    return []

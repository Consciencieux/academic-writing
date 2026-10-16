#!/usr/bin/env python3
"""Locate Chinese prose, table and reference review candidates in LaTeX sources."""
import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

from language_checks import abstract_words, language_hints, repeated_subject, table_cell_hints

SKIP_DIRS = {'build', 'dist', '.git', 'node_modules', 'aux', 'out', '__pycache__', '_minted'}
LEVELS = {'info': 0, 'warn': 1, 'error': 2, 'never': 3}
CODE_BEGIN = re.compile(r'\\begin\{(verbatim\*?|Verbatim|lstlisting|minted|code)\}')
INPUT = re.compile(r'\\(?:input|include)\s*\{([^}]+)\}')
LABEL = re.compile(r'\\label\s*\{([^}]+)\}')
REF = re.compile(r'\\(?:ref|eqref|autoref|Cref|cref|nameref)\*?\s*\{([^}]+)\}')
CITE = re.compile(r'\\(?:[cC]ite[a-zA-Z]*|[pP]arencite|[tT]extcite|[aA]utocite)\*?'
                  r'(?:\s*\[[^\]]*\]){0,2}\s*\{([^}]+)\}')
BIB = re.compile(r'\\(?:addbibresource(?:\[[^\]]*\])?|bibliography)\s*\{([^}]+)\}')
BIB_KEY = re.compile(r'@(?!(?:comment|string|preamble)\b)\w+\s*\{\s*([^,\s]+)', re.I)
MACRO = re.compile(r'\\newcommand\*?\s*\{?\\([A-Za-z@]+)\}?\s*\{([^{}]+)\}')
VALUE = re.compile(r'(?<!\d)(?:\d{4}-\d{2}-\d{2}|\d+(?:\.\d+)?\\?%|\d+\.\d+)(?!\d)')


def strip_comment(line):
    output, i = [], 0
    while i < len(line):
        if line[i] == '\\' and i + 1 < len(line):
            output.append(line[i:i+2]); i += 2
        elif line[i] == '%':
            break
        else:
            output.append(line[i]); i += 1
    return ''.join(output)


def masked_lines(path):
    lines = path.read_text(encoding='utf-8').splitlines()
    output, code_env = [], None
    for raw in lines:
        line = strip_comment(raw)
        if code_env:
            end = '\\end{'+code_env+'}'
            if end not in line:
                output.append(''); continue
            line = line.split(end, 1)[1]; code_env = None
        while True:
            found = CODE_BEGIN.search(line)
            if not found:
                break
            code_env = found.group(1)
            ending = '\\end{'+code_env+'}'
            rest = line[found.end():]
            if ending in rest:
                line = line[:found.start()] + rest.split(ending, 1)[1]; code_env = None
            else:
                line = line[:found.start()]; break
        line = re.sub(r'\\verb\*?([^\w\s]).*?\1', '', line)
        output.append(line)
    return output


def collect(paths):
    found = set()
    for value in paths:
        path = Path(value).resolve()
        if not path.exists():
            raise OSError('Input does not exist: {}'.format(path))
        if path.is_file():
            if path.suffix.lower() != '.tex':
                raise ValueError('Not a .tex file: {}'.format(path))
            found.add(path)
        else:
            for folder, dirs, files in os.walk(str(path)):
                dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
                found.update(Path(folder)/name for name in files if name.endswith('.tex'))
    if not found:
        raise ValueError('No .tex files found')
    return sorted(found)


def resolve(target, main_dir, current_dir, suffix='.tex'):
    if any(token in target for token in ('\\', '#', '$', '://')):
        return None
    for base in (main_dir, current_dir):
        candidate = base / target.strip()
        for file in (candidate, candidate.with_suffix(suffix) if not candidate.suffix else candidate):
            if file.is_file():
                return file.resolve()
    return None


def closure(root, cache):
    visited, pending, unresolved = set(), [root], []
    while pending:
        path = pending.pop()
        if path in visited:
            continue
        visited.add(path)
        if path not in cache:
            cache[path] = masked_lines(path)
        for number, line in enumerate(cache[path], 1):
            for found in INPUT.finditer(line):
                target = resolve(found.group(1), root.parent, path.parent)
                if target:
                    pending.append(target)
                else:
                    unresolved.append((path, number, found.group(1)))
    return sorted(visited), unresolved



def scan_language(path, lines, words, add, max_comma):
    """Scan paragraph units and simple tabular rows while preserving locations."""
    paragraph, start = [], 0
    table, table_header, row, row_start, rows = False, False, [], 0, 0
    title_pending = False

    def hints(text, number, in_table=False):
        for code, standard, message in language_hints(text, words, table=in_table, max_comma=max_comma):
            add(path, number, 'info', code, standard, message, text)
        if not in_table:
            subject = repeated_subject(text)
            if subject:
                add(path, number, 'info', 'L-SUBJECT', 'PROSE-03',
                    '连续以“{}”开头，检查是否机械重复'.format(subject), text)

    def flush():
        nonlocal paragraph
        if paragraph:
            hints(''.join(paragraph), start)
            paragraph = []

    for number, line in enumerate(lines, 1):
        if re.search(r'\\begin\{(?:tabular\*?|tabularx|longtable)\}', line):
            flush(); table, table_header, row, rows = True, True, [], 0
            continue
        if re.search(r'\\end\{(?:tabular\*?|tabularx|longtable)\}', line):
            if row and not table_header:
                text = ' '.join(row)
                hints(text, row_start, True)
                for code, standard, message in table_cell_hints(re.split(r'(?<!\\)&', text)):
                    add(path, row_start, 'info', code, standard, message, text)
            table, row = False, []
            continue
        if table:
            if re.match(r'\s*\\(?:toprule|midrule|bottomrule|hline|cmidrule)\b', line):
                if '\\midrule' in line:
                    table_header = False
                continue
            if not line.strip():
                continue
            if not row:
                row_start = number
            row.append(line.strip())
            if re.search(r'\\\\(?:\[.*?\])?\s*$', line):
                text = ' '.join(row)
                if not table_header:
                    hints(text, row_start, True)
                    for code, standard, message in table_cell_hints(re.split(r'(?<!\\)&', text)):
                        add(path, row_start, 'info', code, standard, message, text)
                    rows += 1
                    if rows == 21:
                        add(path, row_start, 'info', 'T-LONG', 'VIS-03',
                            '表格记录较多，检查分组、跨页与检索效果')
                table_header, row = False, []
            continue
        if re.match(r'\s*\\(?:chapter|section|subsection|subsubsection)\b', line):
            flush(); title_pending = True; continue
        if re.match(r'\s*\\(?:documentclass|usepackage|newcommand|renewcommand|providecommand|input|include|label|begin|end|addbibresource|bibliography|hypersetup|setlength)\b', line):
            flush(); continue
        if not line.strip():
            flush(); continue
        if title_pending:
            if re.match(r'\s*本(?:章|节|部分)', line):
                add(path, number, 'info', 'L-TITLE-ECHO', 'ORG-04', '标题后组织播报，检查是否复述标题', line)
            title_pending = False
        if not paragraph:
            start = number
        paragraph.append(line.strip())
    flush()


def analyze(paths, all_files=False, max_comma=6):
    tex = collect(paths)
    cache = {path: masked_lines(path) for path in tex}
    roots = [p for p in tex if re.search(r'\\documentclass\b', '\n'.join(cache[p]))]
    units, unresolved = [], []
    if all_files or not roots:
        units = [(None, tex)]
    else:
        for root in roots:
            members, missing = closure(root, cache)
            units.append((root, members)); unresolved.extend(missing)
    findings, seen = [], set()

    def add(path, line, severity, code, standard, message, excerpt=''):
        key = (str(path), line, code, message)
        if key in seen:
            return
        seen.add(key)
        findings.append(dict(path=str(path), line=line, severity=severity, code=code,
                             standard=standard, message=message, excerpt=excerpt[:140]))

    for path, number, target in unresolved:
        add(path, number, 'warn', 'S-INPUT', 'tooling/latex.md',
            '静态扫描未解析引入 {}；需由实际构建确认'.format(target))
    active = set(p for _, members in units for p in members)
    for path in sorted(set(tex)-active):
        add(path, 0, 'info', 'S-OUTSIDE', 'tooling/latex.md',
            '此文件处于已识别根文件的静态集合之外，核对其用途')
    words = abstract_words()
    for path in sorted(active):
        scan_language(path, cache[path], words, add, max_comma)
    for root, members in units:
        labels, refs, cites = defaultdict(list), [], []
        bibliography, values = set(), []
        for path in members:
            for number, line in enumerate(cache[path], 1):
                for match in LABEL.finditer(line):
                    labels[match.group(1)].append((path, number))
                for match in REF.finditer(line):
                    refs.extend((path, number, key.strip()) for key in match.group(1).split(','))
                for match in CITE.finditer(line):
                    cites.extend((path, number, key.strip()) for key in match.group(1).split(','))
                for match in BIB.finditer(line):
                    for name in match.group(1).split(','):
                        file = resolve(name, root.parent if root else path.parent, path.parent, '.bib')
                        if file:
                            bibliography.add(file)
                        else:
                            add(path, number, 'warn', 'S-BIB-RESOURCE', 'CITE-05',
                                '未解析文献资源 {}；核对项目配置'.format(name))
                for match in MACRO.finditer(line):
                    if VALUE.fullmatch(match.group(2).strip()):
                        values.append((match.group(1), match.group(2)))
        for key, sites in labels.items():
            if len(sites) > 1:
                add(sites[1][0], sites[1][1], 'warn', 'S-DUP-LABEL', 'VIS-06',
                    '同一静态根范围存在重复标签候选 {}，结合构建配置核对'.format(key))
        for path, number, key in refs:
            if key not in labels:
                add(path, number, 'warn', 'S-REF', 'VIS-06',
                    '静态集合未找到标签 {}，结合外部标签及编译结果核对'.format(key))
        keys = set()
        for file in bibliography:
            keys.update(BIB_KEY.findall(file.read_text(encoding='utf-8')))
        for path, number, key in cites:
            if not bibliography:
                add(path, number, 'info', 'S-CITE-UNVERIFIED', 'CITE-05', '没有可读取的声明书目，引用键未核实')
            elif key not in keys:
                add(path, number, 'warn', 'S-CITE', 'CITE-05', '静态书目未找到引用键 {}'.format(key))
        for path in members:
            for number, line in enumerate(cache[path], 1):
                if MACRO.search(line):
                    continue
                for macro, value in values:
                    if value in line:
                        add(path, number, 'info', 'S-SSOT', 'CONS-01',
                            '发现与宏 \\{} 相同的字面值；核对是否引用同一事实'.format(macro), line)
    return {'scope': 'static-candidates',
            'units': [{'root': str(root) if root else None, 'files': [str(p) for p in members]}
                      for root, members in units],
            'findings': sorted(findings, key=lambda item: (item['path'], item['line'], item['code']))}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='+')
    parser.add_argument('--all-files', action='store_true')
    parser.add_argument('--max-comma', type=int, default=6, help='comma-count hint threshold (default: 6)')
    parser.add_argument('--severity', choices=('info', 'warn', 'error'), default='info')
    parser.add_argument('--fail-on', choices=('never', 'info', 'warn', 'error'), default='error')
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args(argv)
    try:
        if args.max_comma < 1:
            raise ValueError('--max-comma must be positive')
        result = analyze(args.paths, args.all_files, args.max_comma)
    except (OSError, ValueError, UnicodeError) as error:
        print('ERROR: {}'.format(error), file=sys.stderr); return 2
    all_findings = result['findings']
    shown = [f for f in all_findings if LEVELS[f['severity']] >= LEVELS[args.severity]]
    result['findings'] = shown
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for item in shown:
            print('[{severity}] {path}:{line} {code} ({standard}) {message}'.format(**item))
        print('静态候选 {} 项。'.format(len(shown)))
    return int(any(LEVELS[f['severity']] >= LEVELS[args.fail_on] for f in all_findings))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    sys.exit(main())

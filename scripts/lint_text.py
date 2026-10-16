#!/usr/bin/env python3
"""Locate Chinese prose and table review candidates in Markdown and plain text."""
from __future__ import annotations
import argparse
import json
import os
import re
import sys
from pathlib import Path

from language_checks import abstract_words, language_hints, repeated_subject, table_cell_hints

SKIP = {'.git', 'build', 'dist', 'node_modules', '__pycache__'}
LEVELS = {'info': 0, 'warn': 1, 'error': 2, 'never': 3}


def collect(paths: list[str]) -> list[Path]:
    result: set[Path] = set()
    for item in paths:
        p = Path(item).resolve()
        if not p.exists():
            raise OSError(f'Input does not exist: {p}')
        if p.is_file():
            if p.suffix.lower() not in {'.md', '.txt'}:
                raise ValueError(f'Expected Markdown/plain text: {p}')
            result.add(p)
        else:
            for folder, dirs, files in os.walk(p):
                dirs[:] = [d for d in dirs if d not in SKIP]
                result.update(Path(folder) / f for f in files if Path(f).suffix.lower() in {'.md', '.txt'})
    if not result:
        raise ValueError('No Markdown/plain text files found')
    return sorted(result)


def split_row(line: str) -> list[str]:
    # Mask inline code and escaped pipes; this is a controlled pipe-table scan.
    line = re.sub(r'(`+).*?\1', lambda m: m.group().replace('|', '\x00'), line)
    line = line.replace(r'\|', '\x00')
    cells = line.strip().strip('|').split('|')
    return [x.replace('\x00', '|').strip() for x in cells]


def mask(lines: list[str]) -> list[str]:
    out: list[str] = []
    fence: str | None = None
    yaml = bool(lines and lines[0].strip() == '---')
    comment = False
    for i, raw in enumerate(lines):
        if yaml:
            out.append('')
            if i and raw.strip() in {'---', '...'}:
                yaml = False
            continue
        m = re.match(r'^\s*(`{3,}|~{3,})', raw)
        if fence:
            out.append('')
            if m and m[1][0] == fence[0] and len(m[1]) >= len(fence):
                fence = None
            continue
        if m:
            fence = m[1]; out.append(''); continue
        # HTML comments can span lines. Preserve text on both sides.
        text = raw
        if comment:
            if '-->' not in text:
                out.append(''); continue
            text = text.split('-->', 1)[1]; comment = False
        while '<!--' in text:
            before, after = text.split('<!--', 1)
            if '-->' in after:
                text = before + after.split('-->', 1)[1]
            else:
                text = before; comment = True; break
        if re.match(r'^\s*(?:>|#{1,6}\s)', text):
            text = ''
        text = re.sub(r'(`+).*?\1', '', text)
        text = re.sub(r'!\[[^\]]*\]\([^)]*\)', '', text)
        out.append(text)
    return out


def analyze(paths: list[str], max_comma: int = 6, max_cell: int = 120) -> dict:
    if min(max_comma, max_cell) < 1:
        raise ValueError('Candidate thresholds must be positive')
    words = abstract_words()
    findings: list[dict] = []
    files = collect(paths)
    def add(p: Path, n: int, hint, excerpt: str) -> None:
        code, standard, msg = hint
        findings.append(dict(path=str(p), line=n, severity='info', code=code,
                             standard=standard, message=msg, excerpt=excerpt[:140]))
    for p in files:
        raw = p.read_text(encoding='utf-8').splitlines()
        lines = mask(raw) if p.suffix.lower() == '.md' else raw
        paragraph: list[str] = []
        start = 0
        table_rows = 0
        table_columns: int | None = None
        def flush() -> None:
            nonlocal paragraph
            if not paragraph:
                return
            text = ''.join(paragraph)
            for h in language_hints(text, words, max_comma=max_comma):
                add(p, start, h, text)
            subject = repeated_subject(text)
            if subject:
                add(p, start, ('L-SUBJECT', 'PROSE-03', f'连续以“{subject}”开头，检查是否机械重复'), text)
            paragraph = []
        i = 0
        while i < len(lines):
            text = lines[i]
            # A real Markdown separator establishes a table; arbitrary pipes do not.
            next_line = lines[i+1] if i+1 < len(lines) else ''
            is_separator = lambda s: bool('|' in s and all(re.fullmatch(r':?-{3,}:?', c.strip()) for c in split_row(s)))
            if p.suffix.lower() == '.md' and '|' in text and is_separator(next_line):
                flush(); table_columns = len(split_row(text)); table_rows = 0
                i += 2; continue
            if table_columns is not None:
                if '|' in text and text.strip():
                    cells = split_row(text); table_rows += 1
                    if len(cells) != table_columns:
                        add(p, i+1, ('T-COLUMNS', 'VIS-03', '表格列数不一致，核对字段与 Markdown 结构'), text)
                    for h in table_cell_hints(cells, max_cell): add(p, i+1, h, text)
                    for h in language_hints(' '.join(cells), words, table=True, max_comma=max_comma): add(p, i+1, h, text)
                    if table_rows == 21:
                        add(p, i+1, ('T-LONG', 'VIS-03', '表格记录较多，检查分组、分页与检索效果'), text)
                    i += 1; continue
                table_columns = None
            if not text.strip():
                flush()
            else:
                if not paragraph: start = i+1
                paragraph.append(text.strip())
            i += 1
        flush()
        # Heading echo cannot be inferred after masking; compare raw heading to next visible paragraph.
        if p.suffix.lower() == '.md':
            for i, text in enumerate(raw):
                if re.match(r'^#{1,6}\s', text):
                    following = next((j for j in range(i+1, len(lines)) if lines[j].strip()), None)
                    if following is not None and re.match(r'\s*本[章节部分]', lines[following]):
                        add(p, following+1, ('L-TITLE-ECHO', 'ORG-04', '标题后播报本章/本节，检查是否仅复述标题'), lines[following])
    unique = {(f['path'], f['line'], f['code']): f for f in findings}
    return {'scope': 'static-candidates', 'files': [str(f) for f in files],
            'findings': sorted(unique.values(), key=lambda f: (f['path'], f['line'], f['code']))}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('paths', nargs='+')
    p.add_argument('--max-comma', type=int, default=6, help='comma-count hint threshold (default: 6)')
    p.add_argument('--max-cell', type=int, default=120, help='cell-length hint threshold (default: 120 characters)')
    p.add_argument('--severity', choices=('info','warn','error'), default='info')
    p.add_argument('--fail-on', choices=('never','info','warn','error'), default='error')
    p.add_argument('--json', action='store_true')
    a = p.parse_args(argv)
    try:
        result = analyze(a.paths, a.max_comma, a.max_cell)
    except (OSError, UnicodeError, ValueError) as e:
        print(f'ERROR: {e}', file=sys.stderr); return 2
    all_findings = result['findings']
    result['findings'] = [f for f in all_findings if LEVELS[f['severity']] >= LEVELS[a.severity]]
    if a.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        for f in result['findings']:
            print('[{severity}] {path}:{line} {code} ({standard}) {message}'.format(**f))
        print(f"静态候选 {len(result['findings'])} 项。")
    return int(any(LEVELS[f['severity']] >= LEVELS[a.fail_on] for f in all_findings))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    sys.exit(main())

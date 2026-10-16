#!/usr/bin/env python3
"""Validate the current corpus and build self-contained Agent Skills (stdlib).

--sync copies the single short core into Guide/Audit entry blocks.
--check-only checks current resources, standard IDs, examples and local links.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
EXECUTION = ('academic-writing-guide', 'academic-writing-audit')
ALL_SKILLS = ('academic-writing',) + EXECUTION
DOMAINS = ('evidence', 'organization', 'prose', 'visuals', 'citations', 'consistency')
BEGIN = '<!-- GENERATED:CORE:START -->'
END = '<!-- GENERATED:CORE:END -->'
ZIP_TIME = (2020, 1, 1, 0, 0, 0)
RULE_ID = re.compile(r'^## ((?:EVID|ORG|PROSE|VIS|CITE|CONS)-\d{2})\b', re.M)
LINK = re.compile(r'(?<!!)\[[^\]\n]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)')
SKIP = {'.git', 'dist', '__pycache__', '.DS_Store'}


class PackageError(Exception):
    pass


def skip(path: Path) -> bool:
    return any(p in SKIP or p.startswith('._') or p.endswith('.pyc') for p in path.parts)


def files(root: Path):
    for p in sorted(root.rglob('*')):
        if not skip(p.relative_to(root)) and p.is_file():
            if p.is_symlink():
                raise PackageError(f'Symlink is not a packaged resource: {p}')
            yield p


def core_text(root: Path) -> str:
    text = (root / 'shared/core.md').read_text(encoding='utf-8')
    start, end = '<!-- CORE:START -->', '<!-- CORE:END -->'
    if text.count(start) != 1 or text.count(end) != 1:
        raise PackageError('Missing or duplicated core markers')
    return text.split(start, 1)[1].split(end, 1)[0].strip()


def project_core(root: Path, write: bool = False) -> None:
    core = core_text(root)
    for name in EXECUTION:
        p = root / 'skills' / name / 'SKILL.md'
        text = p.read_text(encoding='utf-8')
        if text.count(BEGIN) != 1 or text.count(END) != 1:
            raise PackageError(f'Missing or duplicated entry core markers: {p}')
        before, rest = text.split(BEGIN, 1)
        _, after = rest.split(END, 1)
        wanted = before + BEGIN + '\n' + core + '\n' + END + after
        if text != wanted:
            if not write:
                raise PackageError(f'Stale core block: {p}; run --sync')
            p.write_text(wanted, encoding='utf-8')


def rewrite_outside_fences(text: str, fn) -> str:
    output: list[str] = []
    fence: str | None = None
    for line in text.splitlines(keepends=True):
        m = re.match(r'^\s*(`{3,}|~{3,})', line)
        if fence:
            output.append(line)
            if m and m[1][0] == fence[0] and len(m[1]) >= len(fence):
                fence = None
        elif m:
            fence = m[1]; output.append(line)
        else:
            output.append(LINK.sub(fn, line))
    return ''.join(output)


def check_links(base: Path) -> None:
    base = base.resolve()
    for p in files(base):
        if p.suffix != '.md':
            continue
        def check(m):
            u = urlsplit(m[1])
            if u.scheme or u.netloc:
                return m[0]
            target = (p.parent / unquote(u.path)).resolve() if u.path else p
            if target != base and base not in target.parents:
                raise PackageError(f'Escaping link: {p} -> {m[1]}')
            if not target.exists():
                raise PackageError(f'Broken link: {p} -> {m[1]}')
            if u.fragment and target.is_file() and target.suffix == '.md':
                anchors = re.findall(r'<a id="([^"]+)"></a>', target.read_text(encoding='utf-8'))
                if unquote(u.fragment) not in anchors:
                    raise PackageError(f'Missing explicit anchor: {p} -> {m[1]}')
            return m[0]
        rewrite_outside_fences(p.read_text(encoding='utf-8'), check)


def validate_entry(p: Path, name: str) -> None:
    text = p.read_text(encoding='utf-8')
    fm = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
    if not fm:
        raise PackageError(f'Missing frontmatter: {p}')
    # Entries in this repository use unquoted one-line scalar fields.
    fields: dict[str, str] = {}
    for line in fm[1].splitlines():
        key, sep, value = line.partition(':')
        if not sep or key in fields:
            raise PackageError(f'Invalid entry field: {p}')
        fields[key] = value.strip()
    if fields.get('name') != name or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name):
        raise PackageError(f'Invalid name: {p}')
    if len(name) > 64 or not 1 <= len(fields.get('description', '')) <= 1024:
        raise PackageError(f'Invalid name/description length: {p}')
    if len(text.splitlines()) >= 500 or not text[fm.end():].strip():
        raise PackageError(f'Empty or oversized entry: {p}')


def validate_source(root: Path) -> None:
    needed = ['LICENSE', 'SKILL.md', 'shared/core.md', 'shared/protocols/context.md',
              'scripts/lint_tex.py', 'scripts/lint_text.py', 'scripts/language_checks.py', 'evals/cases.json']
    needed += [f'shared/standards/{d}.md' for d in DOMAINS]
    for n in needed:
        if not (root / n).is_file():
            raise PackageError(f'Missing source: {n}')
    validate_entry(root / 'SKILL.md', 'academic-writing')
    for n in EXECUTION:
        validate_entry(root / 'skills' / n / 'SKILL.md', n)
    project_core(root)
    ids: list[str] = []
    for d in DOMAINS:
        text = (root / f'shared/standards/{d}.md').read_text(encoding='utf-8')
        found = RULE_ID.findall(text)
        if not found:
            raise PackageError(f'No standard IDs: {d}')
        for ident in found:
            if f'<a id="{ident.lower()}"></a>' not in text:
                raise PackageError(f'Missing standard anchor: {ident}')
        ids.extend(found)
    if len(ids) != len(set(ids)):
        raise PackageError('Duplicate standard ID')
    cases = json.loads((root / 'evals/cases.json').read_text(encoding='utf-8'))
    case_ids: set[str] = set()
    for c in cases:
        if c['id'] in case_ids or not c['expected'] or not c['avoid']:
            raise PackageError(f'Invalid eval case: {c["id"]}')
        case_ids.add(c['id'])
        for f in c['fixtures']:
            if not (root / 'evals' / f).is_file():
                raise PackageError(f'Missing eval fixture: {f}')
        if not set(c['standards']).issubset(ids):
            raise PackageError(f'Unknown standard in eval: {c["id"]}')
    check_links(root)


def file_mapping(root: Path, stage: Path, name: str) -> dict[Path, Path]:
    target = stage / name
    mapping = {root / 'LICENSE': target / 'LICENSE'}
    if name == 'academic-writing':
        mapping[root / 'SKILL.md'] = target / 'SKILL.md'
        return mapping
    own = root / 'skills' / name
    mapping.update({p: target / p.relative_to(own) for p in files(own)})
    # Shared layout is identical relative to scripts in source and installed skills.
    for folder in ('shared', 'assets'):
        mapping.update({p: target / folder / p.relative_to(root/folder) for p in files(root/folder)})
    for script in ('lint_tex.py', 'lint_text.py', 'language_checks.py'):
        mapping[root / 'scripts' / script] = target / 'scripts' / script
    return mapping


def rewrite_links(text: str, source: Path, dest: Path, mapping: dict[Path, Path]) -> str:
    def replace(m):
        u = urlsplit(m[1])
        if u.scheme or u.netloc or not u.path:
            return m[0]
        old = (source.parent / unquote(u.path)).resolve()
        if old not in mapping:
            raise PackageError(f'Unpackaged dependency: {source} -> {m[1]}')
        relative = Path(os.path.relpath(mapping[old], dest.parent)).as_posix()
        if u.query: relative += '?' + u.query
        if u.fragment: relative += '#' + u.fragment
        return m[0].replace(m[1], relative, 1)
    return rewrite_outside_fences(text, replace)


def stage_all(root: Path, stage: Path) -> None:
    entry_map = {root / 'SKILL.md': stage / 'academic-writing/SKILL.md'}
    entry_map.update({root/'skills'/n/'SKILL.md': stage/n/'SKILL.md' for n in EXECUTION})
    for n in ALL_SKILLS:
        mapping = file_mapping(root, stage, n)
        lookup = {**entry_map, **mapping}
        for src, dest in mapping.items():
            data = src.read_bytes()
            if src.suffix == '.md':
                data = rewrite_links(data.decode('utf-8'), src, dest, lookup).encode('utf-8')
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
    check_links(stage)
    for n in EXECUTION:
        check_links(stage/n)


def write_zip(dest: Path, stage: Path, names: tuple[str, ...]) -> None:
    with zipfile.ZipFile(dest, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for n in sorted(names):
            for p in files(stage/n):
                info = zipfile.ZipInfo(p.relative_to(stage).as_posix(), ZIP_TIME)
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                z.writestr(info, p.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    with zipfile.ZipFile(dest) as z:
        if z.testzip():
            raise PackageError(f'Corrupt archive: {dest}')


def build(root: Path, output: Path) -> None:
    root = root.resolve()
    validate_source(root)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='academic-writing-build-') as tmp:
        stage = Path(tmp)
        stage_all(root, stage)
        for n in EXECUTION:
            write_zip(output/(n+'.zip'), stage, (n,))
        write_zip(output/'academic-writing-skills.zip', stage, ALL_SKILLS)
    names = sorted(EXECUTION + ('academic-writing-skills',))
    sums = ''.join(f'{hashlib.sha256((output/(n+".zip")).read_bytes()).hexdigest()}  {n}.zip\n' for n in names)
    (output/'SHA256SUMS').write_text(sums, encoding='utf-8')


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--sync', action='store_true')
    p.add_argument('--check-only', action='store_true')
    p.add_argument('--output-dir', default='dist')
    a = p.parse_args(argv)
    try:
        if a.sync:
            project_core(ROOT, write=True)
        if a.sync or a.check_only:
            validate_source(ROOT)
            print('Source resources, links and core blocks passed.')
        else:
            output = Path(a.output_dir)
            build(ROOT, output if output.is_absolute() else ROOT/output)
            print(f'Built Guide, Audit and bundle: {output}')
        return 0
    except (PackageError, OSError, ValueError, KeyError) as e:
        print(f'ERROR: {e}', file=sys.stderr); return 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    sys.exit(main())

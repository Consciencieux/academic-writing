#!/usr/bin/env python3
"""Validate skill resources and build the Guide, Audit and combined ZIP packages."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.parse import unquote, urlsplit
import zipfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
EXECUTION = ('academic-writing-guide', 'academic-writing-audit')
ALL_SKILLS = ('academic-writing',) + EXECUTION
DOMAINS = ('evidence', 'organization', 'prose', 'visuals', 'citations', 'consistency')
SCRIPTS = ('lint_tex.py', 'lint_text.py', 'language_checks.py')
SKIP = {'.git', 'dist', '__pycache__', '.DS_Store', '.pytest_cache', '.venv'}
RULE_ID = re.compile(r'^## ((?:EVID|ORG|PROSE|VIS|CITE|CONS)-\d{2})\b', re.M)
LINK = re.compile(r'(?<!!)\[[^\]\n]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)')


class PackageError(ValueError):
    """A required source resource or reference needs correction."""


def files(root: Path):
    for path in sorted(root.rglob('*')):
        parts = path.relative_to(root).parts
        if any(p in SKIP or p.startswith('._') or p.endswith('.pyc') for p in parts):
            continue
        if parts[:2] == ('evals', 'runs'):
            continue
        if path.is_file():
            yield path


def rewrite_outside_fences(text: str, replace) -> str:
    """Visit the repository's inline Markdown links, leaving code examples intact."""
    output = []
    fence = None
    for line in text.splitlines(keepends=True):
        marker = re.match(r'^\s*(`{3,}|~{3,})', line)
        if fence:
            output.append(line)
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence):
                fence = None
        elif marker:
            fence = marker[1]
            output.append(line)
        else:
            output.append(LINK.sub(replace, line))
    return ''.join(output)


def local_target(source: Path, path: str) -> Path:
    # Keep lexical file names so source symlinks become normal packaged files.
    return Path(os.path.abspath(source.parent / unquote(path)))


def check_links(root: Path) -> None:
    for source in files(root):
        if source.suffix != '.md':
            continue

        def check(match):
            url = urlsplit(match[1])
            if url.scheme or url.netloc:
                return match[0]
            target = local_target(source, url.path) if url.path else source
            if not target.exists():
                raise PackageError(f'{source}: missing link target {match[1]}')
            if url.fragment and target.suffix == '.md' and target.is_file():
                body = target.read_text(encoding='utf-8')
                anchors = re.findall(r'<a id="([^"]+)"></a>', body)
                if unquote(url.fragment) not in anchors:
                    raise PackageError(f'{source}: missing anchor {match[1]}')
            return match[0]

        rewrite_outside_fences(source.read_text(encoding='utf-8'), check)


def validate_entry(path: Path, name: str) -> None:
    text = path.read_text(encoding='utf-8-sig')
    front = re.match(r'\A---\s*\n(.*?)\n---\s*\n', text, re.S)
    if front is None:
        raise PackageError(f'{path}: expected YAML frontmatter')
    try:
        fields = yaml.safe_load(front[1])
    except yaml.YAMLError as error:
        raise PackageError(f'{path}: {error}') from error
    if not isinstance(fields, dict) or fields.get('name') != name:
        raise PackageError(f'{path}: name must be {name}')
    description = fields.get('description')
    if not isinstance(description, str) or not 1 <= len(description.strip()) <= 1024:
        raise PackageError(f'{path}: description must contain 1–1024 characters')
    if not text[front.end():].strip():
        raise PackageError(f'{path}: missing skill instructions')


def standard_ids(root: Path) -> set[str]:
    ids: set[str] = set()
    for domain in DOMAINS:
        path = root / 'shared/standards' / f'{domain}.md'
        text = path.read_text(encoding='utf-8')
        found = RULE_ID.findall(text)
        if not found:
            raise PackageError(f'{path}: missing standard IDs')
        for ident in found:
            if ident in ids or f'<a id="{ident.lower()}"></a>' not in text:
                raise PackageError(f'{path}: duplicated ID or missing anchor {ident}')
            ids.add(ident)
    return ids


def validate_source(root: Path) -> None:
    validate_entry(root / 'SKILL.md', 'academic-writing')
    for name in EXECUTION:
        validate_entry(root / 'skills' / name / 'SKILL.md', name)
    for resource in ('LICENSE', 'shared/core.md', 'shared/protocols/context.md'):
        if not (root / resource).is_file():
            raise PackageError(f'Missing resource: {resource}')
    for script in SCRIPTS:
        if not (root / 'scripts' / script).is_file():
            raise PackageError(f'Missing script: {script}')
    standard_ids(root)
    check_links(root)


def file_mapping(root: Path, stage: Path, name: str) -> dict[Path, Path]:
    target = stage / name
    mapping = {root / 'LICENSE': target / 'LICENSE'}
    if name == 'academic-writing':
        mapping[root / 'SKILL.md'] = target / 'SKILL.md'
    else:
        source = root / 'skills' / name
        mapping.update({p: target / p.relative_to(source) for p in files(source)})
        for folder in ('shared', 'assets'):
            mapping.update({p: target / folder / p.relative_to(root / folder)
                            for p in files(root / folder)})
        for script in SCRIPTS:
            mapping[root / 'scripts' / script] = target / 'scripts' / script
    return mapping


def rewrite_links(text: str, source: Path, destination: Path,
                  mapping: dict[Path, Path]) -> str:
    def replace(match):
        url = urlsplit(match[1])
        if url.scheme or url.netloc or not url.path:
            return match[0]
        target = local_target(source, url.path)
        if target not in mapping:
            raise PackageError(f'{source}: package needs resource {match[1]}')
        relative = Path(os.path.relpath(mapping[target], destination.parent)).as_posix()
        if url.query:
            relative += '?' + url.query
        if url.fragment:
            relative += '#' + url.fragment
        return match[0].replace(match[1], relative, 1)
    return rewrite_outside_fences(text, replace)


def stage_all(root: Path, stage: Path) -> None:
    entries = {root / 'SKILL.md': stage / 'academic-writing/SKILL.md'}
    entries.update({root / 'skills' / n / 'SKILL.md': stage / n / 'SKILL.md'
                    for n in EXECUTION})
    for name in ALL_SKILLS:
        mapping = file_mapping(root, stage, name)
        for source, destination in mapping.items():
            data = source.read_bytes()
            if source.suffix == '.md':
                text = rewrite_links(data.decode('utf-8'), source, destination, entries | mapping)
                data = text.encode('utf-8')
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
    check_links(stage)


def build(root: Path, output: Path) -> None:
    root = root.resolve()
    validate_source(root)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='academic-writing-') as temp:
        stage = Path(temp)
        stage_all(root, stage)
        packages = {name: (name,) for name in EXECUTION}
        packages['academic-writing-skills'] = ALL_SKILLS
        for name, members in packages.items():
            with zipfile.ZipFile(output / f'{name}.zip', 'w', zipfile.ZIP_DEFLATED) as archive:
                for member in members:
                    for path in files(stage / member):
                        archive.write(path, path.relative_to(stage).as_posix())
    sums = ''.join(f'{hashlib.sha256((output / (name + ".zip")).read_bytes()).hexdigest()}  {name}.zip\n'
                   for name in packages)
    (output / 'SHA256SUMS').write_text(sums, encoding='utf-8')


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-only', action='store_true', help='validate source resources and links')
    parser.add_argument('--output-dir', default='dist', help='directory for generated ZIP packages')
    args = parser.parse_args(argv)
    try:
        if args.check_only:
            validate_source(ROOT)
            print('Source resources and links passed.')
        else:
            output = Path(args.output_dir)
            build(ROOT, output if output.is_absolute() else ROOT / output)
            print(f'Built Guide, Audit and bundle: {output}')
        return 0
    except (OSError, ValueError) as error:
        print(f'ERROR: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
    sys.exit(main())

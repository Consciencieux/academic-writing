#!/usr/bin/env python3
"""Build self-contained skills from one source corpus (Python 3.8+, stdlib).

--sync updates ONLY the generated core blocks in the two execution entries.
--check-only validates source files, links, rule IDs, and core projections.
Normal mode additionally validates installed links and writes reproducible ZIPs.
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
EXECUTION = ('academic-writing-guide', 'academic-writing-audit')
ALL_SKILLS = ('academic-writing',) + EXECUTION
BEGIN = '<!-- GENERATED:CORE:START -->'
END = '<!-- GENERATED:CORE:END -->'
ZIP_TIME = (2020, 1, 1, 0, 0, 0)
RULE_ID = re.compile(r'^## ((?:EVID|ORG|PROSE|VIS|CITE|CONS)-\d{2})\b', re.M)
LINK = re.compile(r'(?<!!)\[[^\]\n]*\]\(([^\s)]+)(?:\s+"[^"]*")?\)')


class PackageError(Exception):
    pass


def digest(data):
    return hashlib.sha256(data).hexdigest()


def core_text(root):
    text = (root / 'shared/core.md').read_text(encoding='utf-8')
    return text.split('<!-- CORE:START -->', 1)[1].split('<!-- CORE:END -->', 1)[0].strip()


def project_core(root, write=False):
    core = core_text(root)
    for name in EXECUTION:
        file = root / 'skills' / name / 'SKILL.md'
        text = file.read_text(encoding='utf-8')
        if text.count(BEGIN) != 1 or text.count(END) != 1:
            raise PackageError('Core markers missing or duplicated: {}'.format(file))
        before, rest = text.split(BEGIN, 1)
        _, after = rest.split(END, 1)
        expected = before + BEGIN + '\n' + core + '\n' + END + after
        if text != expected:
            if write:
                file.write_text(expected, encoding='utf-8')
            else:
                raise PackageError('Stale core projection: {}; run --sync'.format(file))


def without_fences(text):
    return re.sub(r'(?ms)^```[^\n]*\n.*?^```\s*$', '', text)


def links(text):
    return list(LINK.finditer(without_fences(text)))


def check_links(base):
    """Validate controlled local Markdown links, not arbitrary Markdown syntax."""
    base = base.resolve()
    for file in base.rglob('*.md'):
        if any(p in {'.git', 'dist', '__pycache__'} for p in file.relative_to(base).parts):
            continue
        text = file.read_text(encoding='utf-8')
        for match in links(text):
            url = urlsplit(match.group(1))
            if url.scheme or url.netloc:
                continue
            target = (file.parent / unquote(url.path)).resolve() if url.path else file
            if target != base and base not in target.parents:
                raise PackageError('Escaping link: {} -> {}'.format(file, match.group(1)))
            if not target.exists():
                raise PackageError('Broken link: {} -> {}'.format(file, match.group(1)))
            if url.fragment and target.is_file() and target.suffix == '.md':
                body = target.read_text(encoding='utf-8')
                # Stable standard links use explicit anchors, avoiding title-dependent IDs.
                anchors = set(re.findall(r'<a id="([^"]+)"></a>', body))
                if unquote(url.fragment) not in anchors:
                    raise PackageError('Unknown anchor: {} -> {}'.format(file, match.group(1)))


def validate_entry(file, name):
    text = file.read_text(encoding='utf-8')
    match = re.match(r'\A---\n(.*?)\n---\n', text, re.S)
    if not match:
        raise PackageError('Missing frontmatter: {}'.format(file))
    # The repository deliberately uses scalar, one-line frontmatter fields.
    fields = {}
    for line in match.group(1).splitlines():
        key, sep, value = line.partition(':')
        if not sep or key in fields:
            raise PackageError('Unsupported/duplicate frontmatter field: {}'.format(file))
        fields[key] = value.strip()
    if fields.get('name') != name or not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name):
        raise PackageError('Invalid skill name: {}'.format(file))
    if len(name) > 64 or not 1 <= len(fields.get('description', '')) <= 1024:
        raise PackageError('Invalid name/description length: {}'.format(file))
    if len(text.splitlines()) >= 500 or not text[match.end():].strip():
        raise PackageError('Empty or oversized skill entry: {}'.format(file))


def validate_source(root):
    required = ('LICENSE', 'SKILL.md', 'shared/core.md', 'shared/protocols/context.md',
                'scripts/lint_tex.py', 'evals/cases.json', 'docs/coverage.json')
    for name in required:
        if not (root / name).is_file():
            raise PackageError('Missing source: {}'.format(name))
    validate_entry(root / 'SKILL.md', 'academic-writing')
    for name in EXECUTION:
        validate_entry(root / 'skills' / name / 'SKILL.md', name)
    project_core(root)
    ids = []
    for file in sorted((root / 'shared/standards').glob('*.md')):
        text = file.read_text(encoding='utf-8')
        found = RULE_ID.findall(text)
        if not found:
            raise PackageError('No standard IDs: {}'.format(file))
        for ident in found:
            if '<a id="{}"></a>'.format(ident.lower()) not in text:
                raise PackageError('Missing stable anchor: {}'.format(ident))
        ids.extend(found)
    if len(ids) != len(set(ids)):
        raise PackageError('Duplicate standard ID')
    coverage = json.loads((root / 'docs/coverage.json').read_text(encoding='utf-8'))
    for record in coverage['sections']:
        if not record['targets'] or not record['decision']:
            raise PackageError('Unmapped source section: {}'.format(record))
        for ident in record['targets']:
            if ident not in ids:
                raise PackageError('Unknown coverage target: {}'.format(ident))
    cases = json.loads((root / 'evals/cases.json').read_text(encoding='utf-8'))
    for case in cases:
        for path in case['fixtures']:
            if not (root / 'evals' / path).is_file():
                raise PackageError('Missing eval fixture: {}'.format(path))
        if not set(case['standards']).issubset(set(ids)):
            raise PackageError('Invalid eval standards: {}'.format(case['id']))
    check_links(root)


def file_mapping(root, stage, name):
    target = stage / name
    result = {root / 'LICENSE': target / 'LICENSE'}
    if name == 'academic-writing':
        result[root / 'SKILL.md'] = target / 'SKILL.md'
        return result
    source = root / 'skills' / name
    for path in source.rglob('*'):
        if path.is_file():
            result[path] = target / path.relative_to(source)
    for path in (root / 'shared').rglob('*'):
        if path.is_file() and path.name != 'README.md':
            result[path] = target / 'references' / path.relative_to(root / 'shared')
    for path in (root / 'assets').rglob('*'):
        if path.is_file():
            result[path] = target / 'assets' / path.relative_to(root / 'assets')
    result[root / 'scripts/lint_tex.py'] = target / 'scripts/lint_tex.py'
    return result


def rewrite_links(text, source, destination, mapping):
    # All link replacements are path-based; no guessing between source/install roots.
    def replace(match):
        raw = match.group(1)
        url = urlsplit(raw)
        if url.scheme or url.netloc or not url.path:
            return match.group(0)
        old_target = (source.parent / unquote(url.path)).resolve()
        if old_target not in mapping:
            raise PackageError('Unpackaged dependency: {} -> {}'.format(source, raw))
        relative = Path(os.path.relpath(mapping[old_target], destination.parent)).as_posix()
        if url.fragment:
            relative += '#' + url.fragment
        return match.group(0).replace(raw, relative, 1)
    # Our executable Markdown code examples have no link syntax; actual links are checked separately.
    return LINK.sub(replace, text)


def stage_all(root, stage):
    mappings = {name: file_mapping(root, stage, name) for name in ALL_SKILLS}
    entry_map = {root / 'SKILL.md': stage / 'academic-writing/SKILL.md'}
    entry_map.update({root / 'skills' / name / 'SKILL.md': stage / name / 'SKILL.md'
                      for name in EXECUTION})
    for name, mapping in mappings.items():
        references = dict(entry_map)
        references.update(mapping)
        manifest = {}
        for source, dest in sorted(mapping.items(), key=lambda item: str(item[0])):
            if source.is_symlink():
                raise PackageError('Symlink source is not packaged: {}'.format(source))
            data = source.read_bytes()
            original_hash = digest(data)
            if source.suffix == '.md':
                data = rewrite_links(data.decode('utf-8'), source, dest, references).encode('utf-8')
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            manifest[dest.relative_to(stage / name).as_posix()] = {
                'source': source.relative_to(root).as_posix(),
                'source_sha256': original_hash, 'packaged_sha256': digest(data)}
        (stage / name / 'RESOURCE-MANIFEST.json').write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True)+'\n', encoding='utf-8')
    check_links(stage)


def write_zip(file, stage, names):
    with zipfile.ZipFile(file, 'w', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name in sorted(names):
            for path in sorted((stage / name).rglob('*')):
                if not path.is_file():
                    continue
                rel = path.relative_to(stage)
                if any(p in {'__pycache__', '.DS_Store'} or p.startswith('._') or p.endswith('.pyc')
                       for p in rel.parts):
                    raise PackageError('Unexpected cache file: {}'.format(path))
                info = zipfile.ZipInfo(rel.as_posix(), ZIP_TIME)
                info.create_system = 3
                info.external_attr = 0o100644 << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED,
                                 compresslevel=9)
    with zipfile.ZipFile(file) as archive:
        if archive.testzip() is not None:
            raise PackageError('Corrupt ZIP: {}'.format(file))


def build(root, output):
    validate_source(root)
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='academic-writing-') as temp:
        stage = Path(temp)
        stage_all(root, stage)
        for name in EXECUTION:
            write_zip(output / (name+'.zip'), stage, (name,))
        write_zip(output / 'academic-writing-skills.zip', stage, ALL_SKILLS)
    files = [output / (name + '.zip') for name in sorted(EXECUTION + ('academic-writing-skills',))]
    (output / 'SHA256SUMS').write_text(
        ''.join('{}  {}\n'.format(digest(p.read_bytes()), p.name) for p in files), encoding='utf-8')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sync', action='store_true')
    parser.add_argument('--check-only', action='store_true')
    parser.add_argument('--output-dir', default='dist')
    args = parser.parse_args(argv)
    try:
        if args.sync:
            project_core(ROOT, write=True)
        if args.check_only or args.sync:
            validate_source(ROOT)
            print('Source validation passed; no model behavior has been evaluated.')
        if not args.check_only and not args.sync:
            output = Path(args.output_dir)
            if not output.is_absolute():
                output = ROOT / output
            build(ROOT, output)
            print('Built guide, audit and three-skill bundle in {}'.format(output))
        return 0
    except (PackageError, OSError, ValueError, IndexError) as error:
        print('ERROR: {}'.format(error), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())

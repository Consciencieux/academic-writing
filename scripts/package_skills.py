#!/usr/bin/env python3
"""校验并打包 academic-writing 多 Skill（Python 3.8+，仅标准库）。

源代码的共享规则只维护于 shared/rules/；独立安装包内的
references/rules/ 是打包时生成的只读副本。

用法：python3 scripts/package_skills.py [--output-dir dist] [--check-only]
"""

import argparse
import re
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ("academic-writing", "academic-writing-guide", "academic-writing-audit")
STANDALONE = ("academic-writing-guide", "academic-writing-audit")
RULES = (
    "content-and-judgment.md",
    "language.md",
    "structure-and-formatting.md",
    "ssot-and-concept-cleanup.md",
    "latex-mechanics.md",
    "self-check.md",
)
# 固定归档时间与权限使同一输入生成可复现的 ZIP。
ZIP_TIME = (2020, 1, 1, 0, 0, 0)


class PackageError(Exception):
    pass


def require(path):
    if not path.is_file():
        raise PackageError("缺少文件：{}".format(path.relative_to(ROOT)))
    return path


def validate_skill(name):
    path = require(ROOT / "skills" / name / "SKILL.md")
    source = path.read_text(encoding="utf-8")
    fm = re.match(r"\A---\s*\n(.*?)\n---\s*\n", source, re.S)
    if not fm:
        raise PackageError("{} 缺少 YAML frontmatter".format(path.relative_to(ROOT)))
    match = re.search(r"^name:\s*([a-z0-9-]+)\s*$", fm.group(1), re.M)
    if not match or match.group(1) != name:
        raise PackageError("{} 的 name 与所在目录不一致".format(path.relative_to(ROOT)))
    if not re.search(r"^description:\s*\S", fm.group(1), re.M):
        raise PackageError("{} 缺少 description".format(path.relative_to(ROOT)))
    if not source[fm.end():].strip():
        raise PackageError("{} 正文为空".format(path.relative_to(ROOT)))


def validate_source():
    require(ROOT / "SKILL.md")
    require(ROOT / "LICENSE")
    require(ROOT / "scripts" / "lint_tex.py")
    for rule in RULES:
        require(ROOT / "shared" / "rules" / rule)
    for name in SKILLS:
        validate_skill(name)
    for name, references in (
        ("academic-writing-guide", ("chapter-methods.md", "revision-workflows.md", "examples.md")),
        ("academic-writing-audit", ("full-document-audit.md",)),
    ):
        for filename in references:
            require(ROOT / "skills" / name / "references" / filename)
    for name in ("preamble-zh.tex", "metadata-macros.tex", "table-and-figure.tex"):
        require(ROOT / "assets" / name)


def copy_directory_if_exists(src, dst):
    if src.exists():
        shutil.copytree(src, dst, dirs_exist_ok=True)


def stage_skill(name, stage):
    target = stage / name
    target.mkdir(parents=True)
    shutil.copy2(ROOT / "skills" / name / "SKILL.md", target / "SKILL.md")
    shutil.copy2(ROOT / "LICENSE", target / "LICENSE")
    copy_directory_if_exists(ROOT / "skills" / name / "references", target / "references")

    if name != "academic-writing":
        (target / "references" / "rules").mkdir(parents=True, exist_ok=True)
        for rule in RULES:
            shutil.copy2(ROOT / "shared" / "rules" / rule,
                         target / "references" / "rules" / rule)
    if name == "academic-writing-audit":
        (target / "scripts").mkdir(exist_ok=True)
        shutil.copy2(ROOT / "scripts" / "lint_tex.py", target / "scripts" / "lint_tex.py")
        copy_directory_if_exists(ROOT / "assets", target / "assets")
    return target


def skip(path):
    return any(part in {"__pycache__", ".DS_Store"} or
               part.startswith("._") or part.endswith(".pyc")
               for part in path.parts)


def make_zip(path, sources, base):
    """sources: 归档内要包含的目录，相对 base 保留结构。"""
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as out:
        for directory in sources:
            for source in sorted(directory.rglob("*")):
                if not source.is_file():
                    continue
                relative = source.relative_to(base)
                if skip(relative):
                    continue
                info = zipfile.ZipInfo(relative.as_posix(), date_time=ZIP_TIME)
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                out.writestr(info, source.read_bytes(), compress_type=zipfile.ZIP_DEFLATED,
                             compresslevel=9)
    with zipfile.ZipFile(path) as check:
        if check.testzip() is not None:
            raise PackageError("ZIP 校验失败：{}".format(path))
        names = set(check.namelist())
        for directory in sources:
            if directory.relative_to(base).as_posix() + "/SKILL.md" not in names:
                raise PackageError("ZIP 中缺少 SKILL.md：{}".format(path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="dist", help="相对仓库根目录的输出目录，或绝对路径")
    parser.add_argument("--check-only", action="store_true", help="仅校验源代码资源是否齐全")
    args = parser.parse_args()

    try:
        validate_source()
        if args.check_only:
            print("Skill 源码检查通过（3 个 Skill、6 份共享规则及附属资源）")
            return 0

        out = Path(args.output_dir)
        if not out.is_absolute():
            out = ROOT / out
        out.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="academic-writing-skills-") as temp:
            staging = Path(temp)
            staged = {name: stage_skill(name, staging) for name in SKILLS}
            for name in STANDALONE:
                make_zip(out / (name + ".zip"), [staged[name]], staging)
            make_zip(out / "academic-writing-skills.zip",
                     [staged[name] for name in SKILLS], staging)
        for name in ("academic-writing-guide.zip", "academic-writing-audit.zip", "academic-writing-skills.zip"):
            print("已生成：{}".format(out / name))
        return 0
    except (PackageError, OSError, zipfile.BadZipFile) as error:
        print("ERROR: {}".format(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

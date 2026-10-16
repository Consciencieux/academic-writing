import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import package_skills as package
import lint_tex as lint
import language_checks


class RepositoryTests(unittest.TestCase):
    def test_source_validation(self):
        package.validate_source(ROOT)

    def test_entries_reference_shared_core(self):
        core = (ROOT / 'shared/core.md').read_text(encoding='utf-8').strip()
        for name in package.EXECUTION:
            text = (ROOT / 'skills' / name / 'SKILL.md').read_text(encoding='utf-8')
            self.assertIn('(../../shared/core.md)', text)
            self.assertNotIn(core, text)

    def test_yaml_quotes_and_multiline_description(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'SKILL.md'
            path.write_text('---\nname: "sample"\ndescription: >-\n  A multi-line\n  description.\nmetadata:\n  owner: "example"\n---\n# Instructions\nWrite.\n', encoding='utf-8')
            package.validate_entry(path, 'sample')

    def test_entry_length_is_not_an_artificial_gate(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'SKILL.md'
            path.write_text('---\nname: sample\ndescription: Example\n---\n' + 'An instruction.\n' * 510, encoding='utf-8')
            package.validate_entry(path, 'sample')

    def test_bad_link_reports_target(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'a.md').write_text('[ref](missing.md)', encoding='utf-8')
            with self.assertRaisesRegex(package.PackageError, 'missing.md'):
                package.check_links(root)

    def test_bad_rule_anchor_reports_reference(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'a.md').write_text('[ref](b.md#unknown)', encoding='utf-8')
            (root / 'b.md').write_text('# Text\n', encoding='utf-8')
            with self.assertRaisesRegex(package.PackageError, 'unknown'):
                package.check_links(root)

    def test_code_example_links_keep_their_text(self):
        text = '```md\n[example](missing.md)\n```\n'
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'a.md').write_text(text, encoding='utf-8')
            package.check_links(root)
            self.assertEqual(package.rewrite_links(text, root / 'a.md', root / 'b.md', {}), text)

    def test_eval_resources_and_rule_references(self):
        ids = package.standard_ids(ROOT)
        cases = json.loads((ROOT / 'evals/cases.json').read_text(encoding='utf-8'))
        self.assertEqual(len(cases), len({c['id'] for c in cases}))
        for case in cases:
            with self.subTest(case=case['id']):
                self.assertTrue(case['expected'] and case['avoid'])
                self.assertTrue(set(case['standards']) <= ids)
                for fixture in case['fixtures']:
                    self.assertTrue((ROOT / 'evals' / fixture).is_file())
        self.assertTrue(any('turns' in c for c in cases))

    def test_detected_hints_reference_current_standards(self):
        words = language_checks.abstract_words()
        sample = '本节将介绍。实现队列化、并发化；完成链路化、流程化。**关键**形成“闭环”体系。' + '（补充）' * 3
        for hint in language_checks.language_hints(sample, words):
            self.assertIn(hint.standard, package.standard_ids(ROOT))

    def test_packaged_resources_and_tools(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            out = root / 'out'
            package.build(ROOT, out)
            for name in package.EXECUTION + ('academic-writing-skills',):
                dst = root / name
                with zipfile.ZipFile(out / (name + '.zip')) as archive:
                    archive.extractall(dst)
                    expected = set(package.ALL_SKILLS) if name == 'academic-writing-skills' else {name}
                    self.assertEqual({p.split('/')[0] for p in archive.namelist()}, expected)
                package.check_links(dst)
                roles = package.EXECUTION if name == 'academic-writing-skills' else (name,)
                for role in roles:
                    base = dst / role
                    self.assertEqual((base / 'shared/core.md').read_bytes(), (ROOT / 'shared/core.md').read_bytes())
                    sample = root / 'sample.md'
                    sample.write_text('实现队列化、并发化；完成链路化、流程化。**关键优势**。', encoding='utf-8')
                    result = subprocess.run([sys.executable, str(base / 'scripts/lint_text.py'), str(sample), '--json'], capture_output=True, encoding='utf-8', check=True)
                    self.assertIn('L-BOLD', {f['code'] for f in json.loads(result.stdout)['findings']})
                    tex = root / 'sample.tex'
                    tex.write_text('\\documentclass{article}\n\\textbf{关键优势}。', encoding='utf-8')
                    result = subprocess.run([sys.executable, str(base / 'scripts/lint_tex.py'), str(tex), '--json'], capture_output=True, encoding='utf-8', check=True)
                    self.assertIn('L-BOLD', {f['code'] for f in json.loads(result.stdout)['findings']})

    def test_file_symlink_and_cache_handling(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'real.md').write_text('Text\n', encoding='utf-8')
            try:
                (root / 'linked.md').symlink_to(root / 'real.md')
            except OSError:
                self.skipTest('File symlinks unavailable on this runner')
            (root / '._cache').write_text('cache', encoding='utf-8')
            (root / 'module.pyc').write_bytes(b'cache')
            found = {p.name for p in package.files(root)}
            self.assertEqual(found, {'real.md', 'linked.md'})


class LintTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def write(self,name,text):
        p=self.root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(text,encoding='utf-8');return p
    def findings(self): return lint.analyze([str(self.root)])['findings']

    def test_comments_masked(self):
        self.write('main.tex','\\documentclass{article}\n% \\ref{missing} 显著\n')
        self.assertEqual(self.findings(),[])
    def test_code_environment_masked(self):
        self.write('main.tex','\\documentclass{article}\n\\begin{verbatim}\n\\ref{missing} **关键** Agent 已完成\n\\end{verbatim}\n')
        self.assertEqual(self.findings(),[])
    def test_escaped_percent(self): self.assertEqual(lint.strip_comment(r'10\% text % comment'),r'10\% text ')
    def test_multiple_roots_isolated(self):
        for n in ('a','b'):self.write(n+'.tex','\\documentclass{article}\n\\label{x}\\ref{x}\n')
        self.assertFalse(any(f['code']=='S-DUP-LABEL' for f in self.findings()))
    def test_duplicate_label_candidate(self):
        self.write('main.tex','\\documentclass{article}\n\\label{x}\\label{x}\n')
        self.assertEqual(self.findings()[0]['severity'],'warn')
    def test_optional_cite_arguments(self):
        self.write('main.tex','\\documentclass{article}\n'+r'\addbibresource{refs.bib}'+'\n'+r'\textcite[see][p. 2]{valid}')
        self.write('refs.bib','@article{valid, title={Synthetic test}}')
        self.assertFalse(any(f['code']=='S-CITE' for f in self.findings()))
    def test_unverified_bibliography(self):
        self.write('main.tex','\\documentclass{article}\n'+r'\cite{unknown}')
        self.assertIn('S-CITE-UNVERIFIED',{f['code'] for f in self.findings()})
    def test_missing_ref_candidate(self):
        self.write('main.tex','\\documentclass{article}\n'+r'\ref{external}')
        self.assertEqual(self.findings()[0]['severity'],'warn')
    def test_negated_zero_not_verdict(self):
        self.write('main.tex','\\documentclass{article}\n缺失不等于 0。\n')
        self.assertFalse(any(f['severity']=='error' for f in self.findings()))
    def test_outside_fragment_not_deleted(self):
        self.write('main.tex',r'\documentclass{article}');self.write('fragment.tex','普通片段')
        self.assertEqual(self.findings()[0]['code'],'S-OUTSIDE')
    def test_include_closure(self):
        self.write('main.tex','\\documentclass{article}\n'+r'\input{chapters/method}')
        self.write('chapters/method.tex',r'\label{a}\ref{a}')
        self.assertFalse(any(f['code']=='S-INPUT' for f in self.findings()))
    def test_default_shows_style_without_failure(self):
        self.write('main.tex','\\documentclass{article}\n'+r'\textbf{关键优势}。')
        output=io.StringIO()
        with contextlib.redirect_stdout(output):self.assertEqual(lint.main([str(self.root)]),0)
        self.assertIn('L-BOLD',output.getvalue())
    def test_explicit_failure_threshold(self):
        self.write('main.tex','\\documentclass{article}\n'+r'\ref{missing}')
        with contextlib.redirect_stdout(io.StringIO()):self.assertEqual(lint.main([str(self.root),'--fail-on','warn']),1)
    def test_invalid_input(self):
        with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(lint.main([str(self.root/'missing.tex')]),2)
    def test_unicode_input_failure(self):
        (self.root/'bad.tex').write_bytes(b'\xff\xfe')
        with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(lint.main([str(self.root)]),2)
    def test_same_value_only_hint(self):
        self.write('main.tex','\\documentclass{article}\n'+r'\newcommand{\A}{90\%}'+'\n'+r'另一指标为90\%。')
        f=[f for f in self.findings() if f['code']=='S-SSOT'];self.assertEqual(len(f),1);self.assertEqual(f[0]['severity'],'info')
    def test_tex_header_and_code_bold_exempt(self):
        self.write('main.tex',r'''\documentclass{article}
\begin{tabular}{ll}
\textbf{对象} & \textbf{数值} \\
\midrule
A & 1 \\
\end{tabular}''')
        self.assertNotIn('L-BOLD',{f['code'] for f in self.findings()})
    def test_tex_body_bold_detected(self):
        self.write('main.tex','\\documentclass{article}\n'+r'具有\textbf{关键优势}。')
        self.assertIn('L-BOLD',{f['code'] for f in self.findings()})
    def test_multiline_telegraph(self):
        self.write('main.tex','\\documentclass{article}\n实现队列化、并发化；\n完成链路化、流程化。')
        self.assertIn('L-TELEGRAPH',{f['code'] for f in self.findings()})
    def test_tex_long_cell(self):
        self.write('main.tex',r'''\documentclass{article}
\begin{tabular}{ll}
对象 & 说明 \\
\midrule
A & '''+'这是放进单元格的一整段解释。'*15+r''' \\
\end{tabular}''')
        self.assertIn('T-LONG-CELL',{f['code'] for f in self.findings()})

if __name__=='__main__':unittest.main()

import contextlib
import importlib.util
import io
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import package_skills as package
import lint_tex as lint


class RepositoryTests(unittest.TestCase):
    def test_source_validation(self):
        package.validate_source(ROOT)

    def test_exact_entry_set(self):
        entries = {p.relative_to(ROOT).as_posix() for p in ROOT.rglob('SKILL.md') if 'dist' not in p.parts}
        self.assertEqual(entries, {'SKILL.md', 'skills/academic-writing-guide/SKILL.md', 'skills/academic-writing-audit/SKILL.md'})

    def test_core_is_exact_projection(self):
        expected = package.core_text(ROOT)
        for name in package.EXECUTION:
            text = (ROOT/'skills'/name/'SKILL.md').read_text(encoding='utf-8')
            self.assertEqual(text.split(package.BEGIN)[1].split(package.END)[0].strip(), expected)

    def test_stale_core_rejected_and_sync_restores(self):
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp)
            shutil.copytree(ROOT/'shared', clone/'shared')
            shutil.copytree(ROOT/'skills', clone/'skills')
            p = clone/'skills/academic-writing-guide/SKILL.md'
            p.write_text(p.read_text(encoding='utf-8').replace('CORE-02', 'WRONG', 1), encoding='utf-8')
            with self.assertRaises(package.PackageError): package.project_core(clone)
            package.project_core(clone, write=True)
            package.project_core(clone)

    def test_broken_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); (p/'a.md').write_text('[x](missing.md)', encoding='utf-8')
            with self.assertRaises(package.PackageError): package.check_links(p)

    def test_escape_link(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); (p/'a.md').write_text('[x](../missing.md)', encoding='utf-8')
            with self.assertRaises(package.PackageError): package.check_links(p)

    def test_missing_anchor(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); (p/'a.md').write_text('[x](b.md#not-here)', encoding='utf-8')
            (p/'b.md').write_text('# b', encoding='utf-8')
            with self.assertRaises(package.PackageError): package.check_links(p)

    def test_code_example_link_not_followed_or_rewritten(self):
        text = '```md\n[example](missing.md)\n```\n'
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp); (p/'a.md').write_text(text, encoding='utf-8')
            package.check_links(p)
            self.assertEqual(package.rewrite_links(text,p/'a.md',p/'b.md',{}),text)

    def test_writing_base_is_additive_and_directly_linked(self):
        text = (ROOT/'skills/academic-writing-guide/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('只要本次会生成或改写论文中的中文文字',text)
        self.assertIn('(../../shared/standards/prose.md)',text)
        self.assertIn('图注、表内说明、删除后的承接改写',text)
        self.assertIn('即将创建、扩展或重组',text)
        self.assertIn('完整执行 CONS-04',text)
        # Static contract check only; real loading is tested by model scenarios.

    def test_eval_fixtures_and_expectations(self):
        cases = json.loads((ROOT/'evals/cases.json').read_text(encoding='utf-8'))
        self.assertEqual(len(cases),len({c['id'] for c in cases}))
        for c in cases:
            self.assertTrue(c['expected'] and c['avoid'])
            for f in c['fixtures']: self.assertTrue((ROOT/'evals'/f).is_file())
        self.assertTrue(any('turns' in c for c in cases))

    def test_packages_links_and_installed_tools(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); out = root/'out'; package.build(ROOT,out)
            for name in package.EXECUTION + ('academic-writing-skills',):
                dst = root/name
                with zipfile.ZipFile(out/(name+'.zip')) as z:
                    z.extractall(dst)
                    expected = set(package.ALL_SKILLS) if name=='academic-writing-skills' else {name}
                    self.assertEqual({n.split('/')[0] for n in z.namelist()},expected)
                package.check_links(dst)
                skills = package.EXECUTION if name=='academic-writing-skills' else (name,)
                for skill in skills:
                    base = dst/skill
                    self.assertTrue((base/'shared/standards/prose.md').is_file())
                    self.assertTrue((base/'scripts/language_checks.py').is_file())
                    sample = root/'sample.md'; sample.write_text('实现队列化、并发化；完成链路化、流程化。**关键优势**。',encoding='utf-8')
                    r = subprocess.run([sys.executable,str(base/'scripts/lint_text.py'),str(sample),'--json'],
                                       capture_output=True,encoding='utf-8',check=True)
                    self.assertIn('L-BOLD',{f['code'] for f in json.loads(r.stdout)['findings']})
                    tex = root/'sample.tex'; tex.write_text('\\documentclass{article}\n\\textbf{关键优势}。',encoding='utf-8')
                    r = subprocess.run([sys.executable,str(base/'scripts/lint_tex.py'),str(tex),'--json'],
                                       capture_output=True,encoding='utf-8',check=True)
                    self.assertIn('L-BOLD',{f['code'] for f in json.loads(r.stdout)['findings']})

    def test_reproducible_current_toolchain(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=Path(tmp)/'a',Path(tmp)/'b'
            package.build(ROOT,a);package.build(ROOT,b)
            self.assertEqual({p.name:p.read_bytes() for p in a.iterdir()}, {p.name:p.read_bytes() for p in b.iterdir()})


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

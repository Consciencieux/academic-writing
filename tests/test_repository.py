import contextlib
import importlib.util
import io
import json
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT/'scripts'/ (name+'.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

package = load('package_skills')
lint = load('lint_tex')

class RepositoryTests(unittest.TestCase):
    def test_source_validation(self):
        package.validate_source(ROOT)

    def test_one_router_source(self):
        self.assertTrue((ROOT/'SKILL.md').is_file())
        self.assertFalse((ROOT/'skills/academic-writing/SKILL.md').exists())
        self.assertEqual(len(list(ROOT.glob('skills/*/SKILL.md'))), 2)

    def test_execution_resources(self):
        guide = ROOT/'skills/academic-writing-guide/references'
        for name in ('argument-design.md', 'draft-and-revise.md', 'source-work.md',
                     'section-moves.md', 'visual-design.md', 'submission.md'):
            self.assertTrue((guide/name).is_file(), name)
        self.assertTrue((ROOT/'skills/academic-writing-audit/references/review-methods.md').is_file())
        for domain in ('evidence', 'organization', 'prose', 'visuals', 'citations', 'consistency'):
            self.assertTrue((ROOT/'shared/standards'/(domain+'.md')).is_file(), domain)

    def test_cases_have_positive_and_negative_expectations(self):
        cases = json.loads((ROOT/'evals/cases.json').read_text(encoding='utf-8'))
        self.assertEqual(len({x['id'] for x in cases}), len(cases))
        self.assertGreaterEqual(len(cases), 12)
        self.assertTrue(all(x['expected'] and x['avoid'] for x in cases))

    def test_core_is_exact_projection(self):
        expected = package.core_text(ROOT)
        for name in package.EXECUTION:
            text = (ROOT/'skills'/name/'SKILL.md').read_text(encoding='utf-8')
            self.assertEqual(text.split(package.BEGIN)[1].split(package.END)[0].strip(), expected)

    def test_stale_core_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            clone = Path(tmp)
            shutil.copytree(ROOT/'shared',clone/'shared')
            shutil.copytree(ROOT/'skills',clone/'skills')
            file=clone/'skills/academic-writing-guide/SKILL.md'
            file.write_text(file.read_text(encoding='utf-8').replace('CORE-01','CORE-99',1),encoding='utf-8')
            with self.assertRaises(package.PackageError): package.project_core(clone)
            package.project_core(clone,write=True)
            package.project_core(clone)

    def test_broken_link_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'a.md').write_text('[bad](missing.md)',encoding='utf-8')
            with self.assertRaises(package.PackageError): package.check_links(root)

    def test_escape_link_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'a.md').write_text('[bad](../not-a-dependency.md)',encoding='utf-8')
            with self.assertRaises(package.PackageError): package.check_links(root)

    def test_missing_anchor_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'a.md').write_text('[bad](b.md#x)',encoding='utf-8')
            (root/'b.md').write_text('# Other',encoding='utf-8')
            with self.assertRaises(package.PackageError): package.check_links(root)

    def test_fenced_example_link_not_required(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'a.md').write_text('```text\n[example](not-a-file.md)\n```\n',encoding='utf-8')
            package.check_links(root)

    def test_packaged_skills_resolve_resources(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'out'; package.build(ROOT,out)
            with zipfile.ZipFile(out/'academic-writing-skills.zip') as z:
                names=set(z.namelist())
                for skill in package.ALL_SKILLS:
                    self.assertIn(skill+'/SKILL.md',names)
                for skill in package.EXECUTION:
                    self.assertIn(skill+'/references/standards/evidence.md',names)
                    self.assertIn(skill+'/scripts/lint_tex.py',names)
                    self.assertIn(skill+'/assets/preamble-zh.tex',names)
                stage=Path(tmp)/'extracted'; z.extractall(stage); package.check_links(stage)
            for skill in package.EXECUTION:
                with zipfile.ZipFile(out/(skill+'.zip')) as z:
                    self.assertEqual({p.split('/')[0] for p in z.namelist()},{skill})
                    stage=Path(tmp)/skill; z.extractall(stage); package.check_links(stage)

    def test_build_reproducible_same_toolchain(self):
        with tempfile.TemporaryDirectory() as tmp:
            first, second = Path(tmp)/'first',Path(tmp)/'second'
            package.build(ROOT,first); package.build(ROOT,second)
            self.assertEqual({p.name:p.read_bytes() for p in first.iterdir()},
                             {p.name:p.read_bytes() for p in second.iterdir()})

class LintTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
    def tearDown(self): self.temp.cleanup()
    def write(self,name,text):
        file=self.root/name; file.parent.mkdir(parents=True,exist_ok=True)
        file.write_text(text,encoding='utf-8'); return file
    def findings(self): return lint.analyze([str(self.root)])['findings']

    def test_comments_masked(self):
        self.write('main.tex','\\documentclass{article}\n% \\ref{missing} 显著\n')
        self.assertEqual(self.findings(),[])

    def test_code_environment_masked(self):
        self.write('main.tex','\\documentclass{article}\n\\begin{verbatim}\n\\ref{missing} Agent 已完成\n\\end{verbatim}\n')
        self.assertEqual(self.findings(),[])

    def test_escaped_percent_kept(self):
        self.assertEqual(lint.strip_comment(r'10\% text % comment'),r'10\% text ')

    def test_multiple_roots_not_combined(self):
        for name in ('a','b'):
            self.write(name+'.tex','\\documentclass{article}\n\\label{x}\\ref{x}\n')
        self.assertFalse(any(f['code']=='S-DUP-LABEL' for f in self.findings()))

    def test_static_duplicate_candidate(self):
        self.write('main.tex','\\documentclass{article}\n\\label{x}\\label{x}\n')
        self.assertEqual(self.findings()[0]['severity'],'warn')

    def test_optional_citation_arguments(self):
        self.write('main.tex',r'\documentclass{article}'+'\n'+r'\addbibresource{refs.bib}'+'\n'+r'\textcite[see][p. 2]{valid}')
        self.write('refs.bib','@article{valid, title={Synthetic test}}')
        self.assertFalse(any(f['code']=='S-CITE' for f in self.findings()))

    def test_missing_bibliography_not_claimed_valid(self):
        self.write('main.tex',r'\documentclass{article}'+'\n'+r'\cite{unknown}')
        self.assertIn('S-CITE-UNVERIFIED',{f['code'] for f in self.findings()})

    def test_missing_reference_is_candidate_not_error(self):
        self.write('main.tex',r'\documentclass{article}'+'\n'+r'\ref{external}')
        self.assertEqual(self.findings()[0]['severity'],'warn')

    def test_negated_zero_not_hard_violation(self):
        self.write('main.tex','\\documentclass{article}\n缺失不等于 0。\n')
        self.assertFalse(any(f['severity']=='error' for f in self.findings()))

    def test_outside_fragment_not_deleted_concept(self):
        self.write('main.tex',r'\documentclass{article}')
        self.write('fragment.tex','正常片段')
        self.assertEqual(self.findings()[0]['code'],'S-OUTSIDE')
        self.assertEqual(self.findings()[0]['severity'],'info')

    def test_include_closure(self):
        self.write('main.tex',r'\documentclass{article}'+'\n'+r'\input{chapters/method}')
        self.write('chapters/method.tex',r'\label{a}\ref{a}')
        self.assertFalse(any(f['code']=='S-INPUT' for f in self.findings()))

    def test_default_exit_does_not_fail_on_style(self):
        self.write('main.tex','\\documentclass{article}\n显著提高。\n')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(lint.main([str(self.root),'--severity','info']),0)

    def test_explicit_failure_threshold(self):
        self.write('main.tex',r'\documentclass{article}'+'\n'+r'\ref{missing}')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(lint.main([str(self.root),'--fail-on','warn']),1)

    def test_invalid_input_is_error(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(lint.main([str(self.root/'missing.tex')]),2)

    def test_unicode_parse_failure_is_error(self):
        (self.root/'bad.tex').write_bytes(b'\xff\xfe')
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(lint.main([str(self.root)]),2)

    def test_same_value_only_hint(self):
        self.write('main.tex',r'\documentclass{article}'+'\n'+r'\newcommand{\A}{90\%}'+'\n'+r'另一指标为90\%。')
        f=[f for f in self.findings() if f['code']=='S-SSOT']
        self.assertEqual(len(f),1); self.assertEqual(f[0]['severity'],'info')

if __name__=='__main__': unittest.main()

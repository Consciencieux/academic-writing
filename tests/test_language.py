import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import language_checks as checks
import lint_text


class LanguageTests(unittest.TestCase):
    def setUp(self):self.words=checks.abstract_words()
    def codes(self,s,**kw):return {h.code for h in checks.language_hints(s,self.words,**kw)}
    def test_normative_word_list(self):
        self.assertEqual(len(self.words),18)
        self.assertIn('赋能',self.words);self.assertIn('闭环',self.words);self.assertIn('增强',self.words)
    def test_word_list_changes_follow_source(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'prose.md';p.write_text('## PROSE-11 用词\n> 词一、词二\n## PROSE-12 其他\n',encoding='utf-8')
            self.assertEqual(checks.abstract_words(p),('词一','词二'))
    def test_missing_word_resource_fails(self):
        with tempfile.TemporaryDirectory() as t:
            with self.assertRaises(OSError):checks.abstract_words(Path(t)/'missing.md')
    def test_abstract_cluster(self):self.assertIn('L-ABSTRACT',self.codes('赋能体系，完善闭环。'))
    def test_single_technical_word_not_cluster(self):self.assertNotIn('L-ABSTRACT',self.codes('反馈信号构成闭环。'))
    def test_telegraph(self):self.assertIn('L-TELEGRAPH',self.codes('实现队列化承载、并发化调度；完成链路化、流程化。'))
    def test_complete_sentences(self):self.assertNotIn('L-TELEGRAPH',self.codes('请求存入队列。空闲线程取出队首请求。'))
    def test_template_labels(self):self.assertIn('L-TEMPLATE',self.codes('事实：提升明显。原因：机制完善。'))
    def test_fixed_table_fields(self):self.assertNotIn('L-TEMPLATE',self.codes('事实：记录。',table=True))
    def test_facets(self):self.assertIn('L-FACET',self.codes('在技术方面，实现处理。在管理方面，完善结构。'))
    def test_bold(self):
        for s in ('**关键优势**','__重要__',r'\textbf{优势明显}'):
            with self.subTest(s=s):self.assertIn('L-BOLD',self.codes(s))
    def test_math_bold_not_prose_bold(self):self.assertNotIn('L-BOLD',self.codes(r'$\mathbf{x}$'))
    def test_decorative_quote(self):self.assertIn('L-QUOTE',self.codes('形成了“重要”的机制。'))
    def test_discussing_a_word(self):self.assertNotIn('L-QUOTE',self.codes('“机制”一词指所讨论的关系。'))
    def test_parentheses(self):self.assertIn('L-PAREN',self.codes('观察（时间）（对象）。'))
    def test_long_parenthesis(self):self.assertIn('L-PAREN-LONG',self.codes('结果（'+'主要条件和解释'*10+'）。'))
    def test_dash(self):self.assertIn('L-DASH',self.codes('结果——解释——还要说明条件。'))
    def test_repeat(self):self.assertIn('L-REPEAT',self.codes('换言之，这意味着结论相同。'))
    def test_exact_repeat(self):self.assertIn('L-REPEAT-EXACT',self.codes('请求依次进入相同队列。请求依次进入相同队列。'))
    def test_long_logic_chain(self):self.assertIn('L-LONGSENT',self.codes('条件，动作，原因，结果，限制，例外，追加。'))
    def test_subject_repeat(self):self.assertEqual(checks.repeated_subject('系统接收。系统存储。系统执行。'),'系统')
    def test_short_cell_not_long(self):self.assertEqual(checks.table_cell_hints(['方法A','100毫秒']),[])


class MarkdownTests(unittest.TestCase):
    def setUp(self):self.t=tempfile.TemporaryDirectory();self.root=Path(self.t.name)
    def tearDown(self):self.t.cleanup()
    def write(self,text):
        p=self.root/'paper.md';p.write_text(text,encoding='utf-8');return p
    def codes(self,text):
        p=self.write(text);return {f['code'] for f in lint_text.analyze([str(p)])['findings']}
    def test_code_heading_quote_exempt(self):
        text='# **方法**\n\n```md\n**关键** 赋能闭环\n```\n\n> **引用** 赋能闭环\n'
        self.assertEqual(self.codes(text),set())
    def test_tilde_fence_exempt(self):self.assertEqual(self.codes('~~~text\n**关键**\n~~~'),set())
    def test_frontmatter_exempt(self):self.assertEqual(self.codes('---\ntitle: **标题**\n---\n普通句子。'),set())
    def test_inline_code_exempt(self):self.assertNotIn('L-BOLD',self.codes('字段是`**label**`。'))
    def test_html_comment_exempt(self):self.assertEqual(self.codes('<!--\n**关键**\n-->'),set())
    def test_table_header_exempt(self):
        self.assertNotIn('L-BOLD',self.codes('| **对象** | **值** |\n| --- | --- |\n| A | 1 |'))
    def test_table_body_bold_candidate(self):
        self.assertIn('L-BOLD',self.codes('| 对象 | 说明 |\n| --- | --- |\n| A | **关键** |'))
    def test_long_table_cell(self):
        self.assertIn('T-LONG-CELL',self.codes('| 对象 | 说明 |\n| --- | --- |\n| A | '+'一段完整的解释。'*20+' |'))
    def test_escaped_pipe(self):self.assertEqual(lint_text.split_row(r'| A\|B | C |'),['A|B','C'])
    def test_column_count_candidate(self):self.assertIn('T-COLUMNS',self.codes('| a | b |\n| --- | --- |\n| a | b | c |'))
    def test_wrapped_line_telegraph(self):self.assertIn('L-TELEGRAPH',self.codes('实现队列化、并发化；\n完成链路化、流程化。'))
    def test_cli_default_displays_style(self):
        p=self.write('**关键优势**。');o=io.StringIO()
        with contextlib.redirect_stdout(o):self.assertEqual(lint_text.main([str(p)]),0)
        self.assertIn('L-BOLD',o.getvalue())
    def test_failure_not_hidden_by_display_filter(self):
        p=self.write('**关键优势**。')
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(lint_text.main([str(p),'--severity','error','--fail-on','info']),1)
    def test_json_contains_traceable_rules(self):
        p=self.write('赋能闭环。');o=io.StringIO()
        with contextlib.redirect_stdout(o):lint_text.main([str(p),'--json'])
        record=json.loads(o.getvalue());self.assertEqual(record['findings'][0]['standard'],'PROSE-11')
    def test_bad_threshold(self):
        p=self.write('文字')
        with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(lint_text.main([str(p),'--max-cell','0']),2)
    def test_bad_input(self):
        with contextlib.redirect_stderr(io.StringIO()):self.assertEqual(lint_text.main([str(self.root/'missing.md')]),2)

if __name__=='__main__':unittest.main()

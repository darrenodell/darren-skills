import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1]/'plugins/crypto-research/skills/html-research-report/scripts/render_report.py'
spec=importlib.util.spec_from_file_location('render_report',path)
renderer=importlib.util.module_from_spec(spec);spec.loader.exec_module(renderer)

class HtmlTests(unittest.TestCase):
    def test_source_html_and_unsafe_links_do_not_execute(self):
        result=renderer.markdown('<script>alert(1)</script>\n\n[bad](javascript:alert) [good](https://example.com)')
        self.assertNotIn('<script>',result)
        self.assertNotIn('href="javascript:',result)
        self.assertIn('href="https://example.com"',result)
        self.assertIn('&lt;script&gt;',result)

    def test_preserves_table_links_lists_and_code(self):
        result=renderer.markdown('# Title\n\n## Risks\n\n| Metric | Value |\n| --- | --- |\n| Close | $123 |\n\n- **Wait** for [evidence](https://example.com)\n\n```text\n<not-an-element>\n```')
        for expected in ['<th scope="col">Metric</th>','<td>$123</td>','<strong>Wait</strong>','https://example.com','&lt;not-an-element&gt;']:
            self.assertIn(expected,result)

    def test_rejects_mismatched_snapshot(self):
        with self.assertRaisesRegex(ValueError,'snapshot ID'):
            renderer.render('Wrong report',{'snapshot_id':'abc','products':[]})

    def test_unclosed_code_and_bad_tables_fail_instead_of_losing_content(self):
        with self.assertRaises(ValueError):renderer.markdown('```\nunfinished')
        with self.assertRaises(ValueError):renderer.markdown('| A | B |\n|---|---|\n| only one |')

if __name__=='__main__':unittest.main()
